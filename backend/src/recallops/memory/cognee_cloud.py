from __future__ import annotations

import asyncio
from dataclasses import asdict, is_dataclass, replace
from io import BytesIO
from pathlib import PurePath
from typing import Any, cast
from uuid import NAMESPACE_URL, UUID, uuid5

import cognee
from cognee.api.v1.serve.cloud_client import CloudClient
from cognee.api.v1.serve.state import set_remote_client
from cognee.modules.search.types import SearchType

from recallops.memory.contract import (
    DatasetStatus,
    EvidencePayload,
    ForgetReceipt,
    ImproveReceipt,
    MemoryHealth,
    RecallEntry,
    RecallReference,
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


class _RemoteOperationUnsupported(RuntimeError):
    pass


def _remembered_data_id(result: object) -> str | None:
    items = result.get("items") if isinstance(result, dict) else getattr(result, "items", None)
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            return cast(str, item["id"])
    return None


class _NamedBytesIO(BytesIO):
    def __init__(self, content: bytes, name: str) -> None:
        super().__init__(content)
        self.name = name


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


def _chunk_references(
    raw: object,
    provider_names: dict[str, str],
) -> tuple[RecallReference, ...]:
    plain = _to_plain(raw)
    rows = plain if isinstance(plain, list) else [plain]
    chunks: list[dict[object, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text_result = row.get("text_result")
        if isinstance(text_result, list):
            chunks.extend(item for item in text_result if isinstance(item, dict))
            continue
        metadata = row.get("metadata")
        raw_item = row.get("raw")
        if isinstance(metadata, dict) and isinstance(raw_item, dict):
            chunks.append({**raw_item, **metadata})

    references: list[RecallReference] = []
    seen_chunks: set[str] = set()
    for chunk in chunks:
        data_id = chunk.get("data_id", chunk.get("document_id"))
        chunk_id = chunk.get("chunk_id", chunk.get("id"))
        document_name = chunk.get("document_name")
        snippet = chunk.get("text", chunk.get("content"))
        if not all(
            isinstance(value, str) and value
            for value in (data_id, chunk_id, document_name, snippet)
        ):
            continue
        normalized_chunk_id = cast(str, chunk_id)
        if normalized_chunk_id in seen_chunks:
            continue
        seen_chunks.add(normalized_chunk_id)
        normalized_data_id = cast(str, data_id)
        normalized_document_name = cast(str, document_name)
        remembered_name = provider_names.get(normalized_data_id)
        if remembered_name is None:
            stem_matches = {
                name
                for name in provider_names.values()
                if PurePath(name).stem == normalized_document_name
            }
            if len(stem_matches) == 1:
                remembered_name = stem_matches.pop()
        references.append(
            RecallReference(
                data_id=normalized_data_id,
                chunk_id=normalized_chunk_id,
                document_name=remembered_name or normalized_document_name,
                snippet=cast(str, snippet),
            ),
        )
    return tuple(references)


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
        self._provider_names: dict[str, str] = {}
        self._provider_data_ids: dict[str, str] = {}
        self._local_provider_data_ids: dict[str, str] = {}
        self._local_evidence_by_stem: dict[str, tuple[str, str] | None] = {}
        self._session_observations: dict[str, str] = {}

    def _canonicalize_reference(
        self,
        reference: RecallReference,
    ) -> RecallReference:
        provider_data_id = reference.data_id
        reference_stem = PurePath(reference.document_name).stem
        local_evidence = self._local_evidence_by_stem.get(reference_stem)
        if local_evidence is not None:
            local_data_id, local_name = local_evidence
            self._provider_data_ids[provider_data_id] = local_data_id
            self._provider_names[provider_data_id] = local_name
            self._local_provider_data_ids[local_data_id] = provider_data_id
            return replace(
                reference,
                data_id=local_data_id,
                document_name=local_name,
            )
        return replace(
            reference,
            data_id=self._provider_data_ids.get(
                provider_data_id,
                reference.data_id,
            ),
            document_name=self._provider_names.get(
                provider_data_id,
                reference.document_name,
            ),
        )

    def _canonicalize_entries(
        self,
        entries: list[RecallEntry],
    ) -> list[RecallEntry]:
        return [
            replace(
                entry,
                references=tuple(
                    self._canonicalize_reference(reference)
                    for reference in entry.references
                ),
            )
            for entry in entries
        ]

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
            if response.status in {404, 405}:
                raise _RemoteOperationUnsupported(path)
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
        content = (
            payload.content
            if isinstance(payload.content, bytes)
            else payload.content.encode("utf-8")
        )
        item = _NamedBytesIO(content, payload.name)
        result = await cognee.remember(
            item,
            dataset_name=payload.dataset,
            self_improvement=False,
            run_in_background=False,
        )
        provider_data_id = _remembered_data_id(result)
        if provider_data_id is None:
            raise RuntimeError("Cognee remember response omitted the provider data ID")
        self._provider_names[provider_data_id] = payload.name
        self._provider_data_ids[provider_data_id] = payload.data_id
        self._local_provider_data_ids[payload.data_id] = provider_data_id
        stem = PurePath(payload.name).stem
        local_evidence = (payload.data_id, payload.name)
        if stem not in self._local_evidence_by_stem:
            self._local_evidence_by_stem[stem] = local_evidence
        elif self._local_evidence_by_stem[stem] != local_evidence:
            self._local_evidence_by_stem[stem] = None
        return RememberReceipt(
            status=_status(result, "completed"),
            data_id=provider_data_id,
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
        self._session_observations[session_id] = content
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
        entries = self._canonicalize_entries(normalize_recall(_to_plain(raw)))
        if not entries or any(entry.references for entry in entries):
            return entries
        try:
            raw_chunks = await cognee.search(
                query_text=request.query,
                query_type=SearchType.CHUNKS,
                datasets=[request.dataset],
                top_k=5,
                verbose=request.include_trace,
            )
        except Exception:
            return entries
        references = _chunk_references(raw_chunks, self._provider_names)
        if not references:
            return entries
        return self._canonicalize_entries(
            [replace(entry, references=references) for entry in entries],
        )

    async def improve_session(
        self,
        dataset: str,
        session_ids: list[str],
    ) -> ImproveReceipt:
        try:
            result = await self._request_json(
                "POST",
                "/api/v1/improve",
                {
                    "dataset_name": dataset,
                    "session_ids": session_ids,
                    "run_in_background": False,
                },
            )
        except _RemoteOperationUnsupported:
            for session_id in session_ids:
                content = self._session_observations.get(session_id)
                if content is None:
                    raise RuntimeError(
                        "Cognee promotion requires a remembered session observation",
                    ) from None
                incident_slug = session_id.removeprefix("incident:").lower()
                receipt = await self.remember_evidence(
                    EvidencePayload(
                        data_id=str(
                            uuid5(
                                NAMESPACE_URL,
                                f"{dataset}:{session_id}:resolution",
                            ),
                        ),
                        name=f"verified-resolution-{incident_slug}.md",
                        content=content,
                        dataset=dataset,
                    ),
                )
                if receipt.status not in {"completed", "running"}:
                    raise RuntimeError("Cognee permanent promotion failed") from None
            return ImproveReceipt(
                status="completed",
                session_ids=tuple(session_ids),
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
        provider_data_id = self._local_provider_data_ids.get(data_id, data_id)
        result = await cognee.forget(
            dataset=dataset,
            data_id=UUID(provider_data_id),
        )
        result_status = _status(result, "deleted")
        normalized_status = (
            "deleted" if result_status in {"completed", "deleted", "success"} else result_status
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
