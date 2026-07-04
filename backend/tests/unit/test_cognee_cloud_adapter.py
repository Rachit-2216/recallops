from types import SimpleNamespace
from uuid import UUID

import pytest

from recallops.memory.cognee_cloud import CogneeCloudAdapter
from recallops.memory.contract import EvidencePayload, RecallRequest

DATA_ID = "2f965daf-7da0-5d7f-987b-4ff2d16c9f77"
REMOTE_DATA_ID = "a16af39d-a8ea-5780-a43c-17b4ba3e1cb3"
SECOND_DATA_ID = "812fc099-53c1-52f6-8200-4fe22ce9ae5d"
ACTUAL_REMOTE_DATA_ID = "ac3f5419-f749-502f-8274-e5a619a9df48"
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
                "answer": "November 18 had the same propagation risk.",
                "search_type": "GRAPH_COMPLETION_CONTEXT_EXTENSION",
                "references": [
                    {
                        "data_id": REMOTE_DATA_ID,
                        "chunk_id": "chunk-1",
                        "document_name": "cloudflare-november-18-postmortem",
                        "snippet": "Configuration propagated across the network.",
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
            name="cloudflare-november-18-postmortem.md",
            content="Configuration propagated across the network.",
            dataset=DATASET,
        ),
    )
    entries = await adapter.recall(
        RecallRequest(
            query="How is December 5 related to November 18?",
            dataset=DATASET,
            session_id="incident:CF-OUTAGE-2025-12-05",
            include_trace=True,
        ),
    )

    assert calls["connect"] == ("https://memory.example.test", "test-key")
    remembered, remember_kwargs = calls["remember"]  # type: ignore[misc]
    assert remembered.name == "cloudflare-november-18-postmortem.md"  # type: ignore[union-attr]
    assert remembered.read() == b"Configuration propagated across the network."  # type: ignore[union-attr]
    assert remember_kwargs == {
        "dataset_name": DATASET,
        "self_improvement": False,
        "run_in_background": False,
    }
    assert calls["recall"] == {
        "query_text": "How is December 5 related to November 18?",
        "datasets": [DATASET],
        "session_id": "incident:CF-OUTAGE-2025-12-05",
        "verbose": True,
        "only_context": False,
        "include_references": True,
    }
    assert receipt.status == "completed"
    assert receipt.data_id == REMOTE_DATA_ID
    assert entries[0].references[0].data_id == DATA_ID
    assert entries[0].references[0].document_name == ("cloudflare-november-18-postmortem.md")


@pytest.mark.asyncio
async def test_cloud_adapter_restores_extension_when_cloud_returns_document_stem(
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
                "search_type": "GRAPH_COMPLETION",
                "text": "The contract item was found.",
                "metadata": {},
                "raw": {},
            },
        ]

    async def fake_search(**_kwargs: object) -> object:
        return [
            {
                "dataset_id": "dataset-1",
                "dataset_name": DATASET,
                "text_result": [
                    {
                        "id": "chunk-1",
                        "document_id": "different-cloud-document-id",
                        "document_name": "recallops-live-contract",
                        "chunk_index": 0,
                        "text": "The marker is amber-orbit-731.",
                    },
                ],
                "context_result": "The marker is amber-orbit-731.",
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
            name="recallops-live-contract.txt",
            content="The marker is amber-orbit-731.",
            dataset=DATASET,
        ),
    )
    entries = await adapter.recall(
        RecallRequest(
            query="Which contract item has the marker?",
            dataset=DATASET,
            session_id="incident:contract-probe",
        ),
    )

    assert entries[0].references[0].data_id == DATA_ID
    assert entries[0].references[0].document_name == ("recallops-live-contract.txt")


@pytest.mark.asyncio
async def test_cloud_adapter_uses_document_identity_when_remember_receipt_id_is_shared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    async def fake_remember(_data: object, **_kwargs: object) -> object:
        return SimpleNamespace(
            status="completed",
            items=[{"id": REMOTE_DATA_ID}],
        )

    async def fake_recall(**_kwargs: object) -> object:
        return [
            {
                "_source": "graph",
                "answer": "The prior outage used the same propagation path.",
                "search_type": "GRAPH_COMPLETION_CONTEXT_EXTENSION",
                "references": [
                    {
                        "data_id": ACTUAL_REMOTE_DATA_ID,
                        "chunk_id": "chunk-prior",
                        "document_name": "cloudflare-november-18-postmortem",
                        "snippet": "Configuration propagated across the network.",
                    },
                ],
            },
        ]

    async def fake_forget(**kwargs: object) -> object:
        calls["forget"] = kwargs
        return {"status": "deleted"}

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
        "recallops.memory.cognee_cloud.cognee.forget",
        fake_forget,
    )

    adapter = CogneeCloudAdapter(
        base_url="https://memory.example.test",
        api_key="test-key",
    )
    await adapter.remember_evidence(
        EvidencePayload(
            data_id=DATA_ID,
            name="cloudflare-november-18-postmortem.md",
            content="Configuration propagated across the network.",
            dataset=DATASET,
        ),
    )
    await adapter.remember_evidence(
        EvidencePayload(
            data_id=SECOND_DATA_ID,
            name="cloudflare-december-5-postmortem.md",
            content="A second incident used the same propagation path.",
            dataset=DATASET,
        ),
    )
    entries = await adapter.recall(
        RecallRequest(
            query="How is this related to the prior incident?",
            dataset=DATASET,
            session_id="incident:CF-OUTAGE-2025-12-05",
        ),
    )
    await adapter.forget_evidence_item(DATASET, DATA_ID)

    assert entries[0].references[0].data_id == DATA_ID
    assert entries[0].references[0].document_name == (
        "cloudflare-november-18-postmortem.md"
    )
    assert calls["forget"] == {
        "dataset": DATASET,
        "data_id": UUID(ACTUAL_REMOTE_DATA_ID),
    }


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
        ["incident:CF-OUTAGE-2025-12-05"],
    )
    forgotten = await adapter.forget_evidence_item(DATASET, DATA_ID)
    status = await adapter.dataset_status(DATASET)
    health = await adapter.health()

    assert calls["request_json"] == (
        "POST",
        "/api/v1/improve",
        {
            "dataset_name": DATASET,
            "session_ids": ["incident:CF-OUTAGE-2025-12-05"],
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
async def test_cloud_adapter_translates_stable_id_for_forget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    async def fake_remember(_data: object, **_kwargs: object) -> object:
        return SimpleNamespace(
            status="completed",
            items=[{"id": REMOTE_DATA_ID}],
        )

    async def fake_forget(**kwargs: object) -> object:
        calls["forget"] = kwargs
        return {"status": "deleted"}

    monkeypatch.setattr(
        "recallops.memory.cognee_cloud._create_remote_client",
        lambda *_: object(),
    )
    monkeypatch.setattr(
        "recallops.memory.cognee_cloud.cognee.remember",
        fake_remember,
    )
    monkeypatch.setattr(
        "recallops.memory.cognee_cloud.cognee.forget",
        fake_forget,
    )

    adapter = CogneeCloudAdapter(
        base_url="https://memory.example.test",
        api_key="test-key",
    )
    await adapter.remember_evidence(
        EvidencePayload(
            data_id=DATA_ID,
            name="cloudflare-november-18-postmortem.md",
            content="Configuration propagated across the network.",
            dataset=DATASET,
        ),
    )
    forgotten = await adapter.forget_evidence_item(DATASET, DATA_ID)

    assert calls["forget"] == {
        "dataset": DATASET,
        "data_id": UUID(REMOTE_DATA_ID),
    }
    assert forgotten.data_id == DATA_ID


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
                "text": "The prior incident had the same propagation risk.",
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
                        "document_name": "cloudflare-november-18-postmortem",
                        "chunk_index": 0,
                        "text": "Configuration propagated across the network.",
                    },
                ],
                "context_result": "Configuration propagated across the network.",
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
            name="cloudflare-november-18-postmortem.md",
            content="Configuration propagated across the network.",
            dataset=DATASET,
        ),
    )
    entries = await adapter.recall(
        RecallRequest(
            query="How is this related to the prior incident?",
            dataset=DATASET,
            session_id="incident:CF-OUTAGE-2025-12-05",
        ),
    )

    assert entries[0].references == (entries[0].references[0],)
    assert entries[0].references[0].data_id == DATA_ID
    assert entries[0].references[0].chunk_id == "chunk-1"
    assert entries[0].references[0].document_name == ("cloudflare-november-18-postmortem.md")
