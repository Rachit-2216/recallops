from __future__ import annotations

import asyncio
from dataclasses import asdict, is_dataclass
from typing import Any, cast
from uuid import UUID

import cognee
from cognee.api.v1.serve.cloud_client import CloudClient
from cognee.api.v1.serve.state import set_remote_client
from cognee.tasks.ingestion.data_item import DataItem

from recallops.memory.contract import (
    DatasetStatus,
    EvidencePayload,
    ForgetReceipt,
    ImproveReceipt,
    MemoryHealth,
    RecallEntry,
    RecallRequest,
    RememberReceipt,
)
from recallops.memory.normalize import normalize_recall


def _status(result: object, default: str) -> str:
    value = getattr(result, "status", None)
    if isinstance(value, str):
        return value
    if isinstance(result, dict):
        dict_value = result.get("status")
        if isinstance(dict_value, str):
            return dict_value
    return default


def _to_plain(value: object) -> object:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_to_plain(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _to_plain(model_dump(mode="python"))
    if is_dataclass(value) and not isinstance(value, type):
        return _to_plain(asdict(value))
    raise TypeError(f"unsupported Cognee response type: {type(value).__name__}")


def _dataset_name(dataset: object) -> str | None:
    if isinstance(dataset, dict):
        name = dataset.get("name")
    else:
        name = getattr(dataset, "name", None)
    return name if isinstance(name, str) else None


def _create_remote_client(base_url: str, api_key: str) -> CloudClient:
    """Connect in memory without Cognee's on-disk credential cache."""
    client = CloudClient(base_url, api_key)
    set_remote_client(client)
    return client


class CogneeCloudAdapter:
    """The only application boundary that depends on Cognee SDK objects."""

    def __init__(self, *, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._client: Any | None = None
        self._connection_lock = asyncio.Lock()

    async def _ensure_connected(self) -> Any:
        if self._client is not None:
            return self._client
        async with self._connection_lock:
            if self._client is None:
                self._client = _create_remote_client(
                    self._base_url,
                    self._api_key,
                )
        return self._client

    async def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, object],
    ) -> object:
        client = await self._ensure_connected()
        request_json = getattr(client, "request_json", None)
        if callable(request_json):
            return await request_json(method, path, payload)

        get_session = getattr(client, "_get_session", None)
        service_url = getattr(client, "service_url", None)
        if not callable(get_session) or not isinstance(service_url, str):
            raise RuntimeError("Cognee remote client cannot make requests")
        session = await get_session()
        async with session.request(
            method,
            f"{service_url}{path}",
            json=payload,
        ) as response:
            if response.status >= 400:
                raise RuntimeError("Cognee remote operation failed")
            return await response.json()

    async def list_datasets(self) -> list[object]:
        """List remote datasets despite Cognee 1.2.2's local-only namespace."""
        client = await self._ensure_connected()
        direct_list = getattr(client, "list_datasets", None)
        if callable(direct_list):
            result = await direct_list()
            return cast(list[object], result)

        get_session = getattr(client, "_get_session", None)
        service_url = getattr(client, "service_url", None)
        if not callable(get_session) or not isinstance(service_url, str):
            raise RuntimeError("Cognee remote client cannot list datasets")
        session = await get_session()
        async with session.get(f"{service_url}/api/v1/datasets") as response:
            if response.status >= 400:
                raise RuntimeError("Cognee dataset listing failed")
            payload = await response.json()
        if not isinstance(payload, list):
            raise RuntimeError("Cognee dataset listing returned an invalid shape")
        return cast(list[object], payload)

    async def remember_evidence(
        self,
        payload: EvidencePayload,
    ) -> RememberReceipt:
        await self._ensure_connected()
        item = DataItem(
            data=payload.content,
            label=payload.name,
            external_metadata={
                "document_name": payload.name,
                "recallops_data_id": payload.data_id,
            },
            data_id=UUID(payload.data_id),
        )
        result = await cognee.remember(
            [item],
            dataset_name=payload.dataset,
            self_improvement=False,
            run_in_background=False,
        )
        return RememberReceipt(
            status=_status(result, "completed"),
            data_id=payload.data_id,
        )

    async def remember_observation(
        self,
        session_id: str,
        content: str,
    ) -> RememberReceipt:
        await self._ensure_connected()
        result = await cognee.remember(
            content,
            session_id=session_id,
            self_improvement=False,
        )
        return RememberReceipt(status=_status(result, "session_stored"))

    async def recall(self, request: RecallRequest) -> list[RecallEntry]:
        await self._ensure_connected()
        raw = await cognee.recall(
            query_text=request.query,
            datasets=[request.dataset],
            session_id=request.session_id,
            verbose=request.include_trace,
            only_context=request.only_context,
            include_references=True,
        )
        return normalize_recall(_to_plain(raw))

    async def improve_session(
        self,
        dataset: str,
        session_ids: list[str],
    ) -> ImproveReceipt:
        result = await self._request_json(
            "POST",
            "/api/v1/improve",
            {
                "dataset_name": dataset,
                "session_ids": session_ids,
                "run_in_background": False,
            },
        )
        return ImproveReceipt(
            status=_status(result, "completed"),
            session_ids=tuple(session_ids),
        )

    async def forget_evidence_item(
        self,
        dataset: str,
        data_id: str,
    ) -> ForgetReceipt:
        await self._ensure_connected()
        result = await cognee.forget(
            dataset=dataset,
            data_id=UUID(data_id),
        )
        result_status = _status(result, "deleted")
        normalized_status = (
            "deleted"
            if result_status in {"completed", "deleted", "success"}
            else result_status
        )
        return ForgetReceipt(status=normalized_status, data_id=data_id)

    async def dataset_status(self, dataset: str) -> DatasetStatus:
        datasets = await self.list_datasets()
        ready = any(_dataset_name(item) == dataset for item in datasets)
        return DatasetStatus(
            dataset=dataset,
            ready=ready,
            status="ready" if ready else "absent",
        )

    async def health(self) -> MemoryHealth:
        try:
            client = await self._ensure_connected()
            health_check = getattr(client, "_health_check", None)
            if callable(health_check):
                reachable = bool(await health_check())
            else:
                await self.list_datasets()
                reachable = True
        except Exception:
            return MemoryHealth(reachable=False, mode="live")
        return MemoryHealth(reachable=reachable, mode="live")
