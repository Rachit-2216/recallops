from types import SimpleNamespace
from uuid import UUID

import pytest

from recallops.memory.cognee_cloud import CogneeCloudAdapter
from recallops.memory.contract import EvidencePayload, RecallRequest

DATA_ID = "2f965daf-7da0-5d7f-987b-4ff2d16c9f77"
REMOTE_DATA_ID = "a16af39d-a8ea-5780-a43c-17b4ba3e1cb3"
DATASET = "recallops_evidence_v1"


@pytest.mark.asyncio
async def test_cloud_adapter_maps_remember_and_recall_to_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    def fake_connect(base_url: str, api_key: str) -> object:
        calls["connect"] = (base_url, api_key)
        return object()

    async def fake_remember(data: object, **kwargs: object) -> object:
        calls["remember"] = (data, kwargs)
        return SimpleNamespace(
            status="completed",
            items=[{"id": REMOTE_DATA_ID}],
        )

    async def fake_recall(**kwargs: object) -> object:
        calls["recall"] = kwargs
        return [
            {
                "_source": "graph",
                "answer": "INC-1842 had the same Redis TTL mismatch.",
                "search_type": "GRAPH_COMPLETION_CONTEXT_EXTENSION",
                "references": [
                    {
                        "data_id": DATA_ID,
                        "chunk_id": "chunk-1",
                        "document_name": "postmortem-inc-1842.md",
                        "snippet": "TTL units were not converted.",
                    },
                ],
            },
        ]

    monkeypatch.setattr(
        "recallops.memory.cognee_cloud._create_remote_client",
        fake_connect,
    )
    monkeypatch.setattr(
        "recallops.memory.cognee_cloud.cognee.remember",
        fake_remember,
    )
    monkeypatch.setattr(
        "recallops.memory.cognee_cloud.cognee.recall",
        fake_recall,
    )

    adapter = CogneeCloudAdapter(
        base_url="https://memory.example.test",
        api_key="test-key",
    )
    receipt = await adapter.remember_evidence(
        EvidencePayload(
            data_id=DATA_ID,
            name="postmortem-inc-1842.md",
            content="TTL units were not converted.",
            dataset=DATASET,
        ),
    )
    entries = await adapter.recall(
        RecallRequest(
            query="How is deploy-418 related to Redis?",
            dataset=DATASET,
            session_id="incident:INC-2048",
            include_trace=True,
        ),
    )

    assert calls["connect"] == ("https://memory.example.test", "test-key")
    remembered, remember_kwargs = calls["remember"]  # type: ignore[misc]
    assert remembered.name == "postmortem-inc-1842.md"  # type: ignore[union-attr]
    assert remembered.read() == b"TTL units were not converted."  # type: ignore[union-attr]
    assert remember_kwargs == {
        "dataset_name": DATASET,
        "self_improvement": False,
        "run_in_background": False,
    }
    assert calls["recall"] == {
        "query_text": "How is deploy-418 related to Redis?",
        "datasets": [DATASET],
        "session_id": "incident:INC-2048",
        "verbose": True,
        "only_context": False,
        "include_references": True,
    }
    assert receipt.status == "completed"
    assert receipt.data_id == REMOTE_DATA_ID
    assert entries[0].references[0].document_name == "postmortem-inc-1842.md"


@pytest.mark.asyncio
async def test_cloud_adapter_maps_lifecycle_and_status_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    class FakeRemoteClient:
        async def request_json(
            self,
            method: str,
            path: str,
            payload: dict[str, object],
        ) -> dict[str, str]:
            calls["request_json"] = (method, path, payload)
            return {"status": "completed"}

        async def list_datasets(self) -> list[object]:
            return [SimpleNamespace(name=DATASET)]

        async def _health_check(self) -> bool:
            return True

    def fake_connect(*_: object) -> object:
        return FakeRemoteClient()

    monkeypatch.setattr(
        "recallops.memory.cognee_cloud._create_remote_client",
        fake_connect,
    )

    async def fake_forget(**kwargs: object) -> object:
        calls["forget"] = kwargs
        return {"status": "deleted"}

    monkeypatch.setattr(
        "recallops.memory.cognee_cloud.cognee.forget",
        fake_forget,
    )
    adapter = CogneeCloudAdapter(base_url="https://memory.test", api_key="key")
    improved = await adapter.improve_session(
        DATASET,
        ["incident:INC-2048"],
    )
    forgotten = await adapter.forget_evidence_item(DATASET, DATA_ID)
    status = await adapter.dataset_status(DATASET)
    health = await adapter.health()

    assert calls["request_json"] == (
        "POST",
        "/api/v1/improve",
        {
            "dataset_name": DATASET,
            "session_ids": ["incident:INC-2048"],
            "run_in_background": False,
        },
    )
    assert calls["forget"] == {
        "dataset": DATASET,
        "data_id": UUID(DATA_ID),
    }
    assert improved.status == "completed"
    assert forgotten.status == "deleted"
    assert status.ready is True
    assert health.reachable is True


@pytest.mark.asyncio
async def test_cloud_adapter_adds_chunk_provenance_when_graph_recall_omits_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_remember(_data: object, **_kwargs: object) -> object:
        return SimpleNamespace(
            status="completed",
            items=[{"id": REMOTE_DATA_ID}],
        )

    async def fake_recall(**_kwargs: object) -> object:
        return [
            {
                "kind": "graph_completion",
                "search_type": "GRAPH_COMPLETION_CONTEXT_EXTENSION",
                "text": "The prior incident had the same TTL mismatch.",
                "metadata": {},
                "raw": {},
            },
        ]

    async def fake_search(**kwargs: object) -> object:
        assert kwargs["datasets"] == [DATASET]
        return [
            {
                "dataset_id": "dataset-1",
                "dataset_name": DATASET,
                "text_result": [
                    {
                        "id": "chunk-1",
                        "document_id": REMOTE_DATA_ID,
                        "document_name": "postmortem-inc-1842",
                        "chunk_index": 0,
                        "text": "TTL units were not converted.",
                    },
                ],
                "context_result": "TTL units were not converted.",
                "objects_result": [],
            },
        ]

    monkeypatch.setattr(
        "recallops.memory.cognee_cloud._create_remote_client",
        lambda *_: object(),
    )
    monkeypatch.setattr(
        "recallops.memory.cognee_cloud.cognee.remember",
        fake_remember,
    )
    monkeypatch.setattr(
        "recallops.memory.cognee_cloud.cognee.recall",
        fake_recall,
    )
    monkeypatch.setattr(
        "recallops.memory.cognee_cloud.cognee.search",
        fake_search,
    )

    adapter = CogneeCloudAdapter(
        base_url="https://memory.example.test",
        api_key="test-key",
    )
    await adapter.remember_evidence(
        EvidencePayload(
            data_id=DATA_ID,
            name="postmortem-inc-1842.md",
            content="TTL units were not converted.",
            dataset=DATASET,
        ),
    )
    entries = await adapter.recall(
        RecallRequest(
            query="How is this related to the prior incident?",
            dataset=DATASET,
            session_id="incident:INC-2048",
        ),
    )

    assert entries[0].references == (
        entries[0].references[0],
    )
    assert entries[0].references[0].data_id == REMOTE_DATA_ID
    assert entries[0].references[0].chunk_id == "chunk-1"
    assert entries[0].references[0].document_name == "postmortem-inc-1842.md"
