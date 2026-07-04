import asyncio
import os
from time import monotonic

import pytest

from recallops.config import Settings
from recallops.memory.cognee_cloud import CogneeCloudAdapter
from recallops.memory.contract import EvidencePayload, RecallEntry, RecallRequest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_COGNEE_INTEGRATION") != "1",
        reason="live Cognee integration is opt-in",
    ),
]

DATASET = "recallops_evidence_v1"
DATA_ID = "d1d38b21-e5e8-59d3-aa7f-613a16fa960d"


async def _recall_until_document_state(
    memory: CogneeCloudAdapter,
    request: RecallRequest,
    *,
    document_name: str,
    present: bool,
    timeout_seconds: float = 90,
) -> list[RecallEntry]:
    deadline = monotonic() + timeout_seconds
    while True:
        recalled = await memory.recall(request)
        document_present = any(
            reference.document_name == document_name
            for entry in recalled
            for reference in entry.references
        )
        if document_present is present:
            return recalled
        if monotonic() >= deadline:
            return recalled
        await asyncio.sleep(5)


@pytest.mark.asyncio
async def test_live_adapter_remember_recall_and_forget_one_contract_item() -> None:
    settings = Settings(_env_file=None)
    assert settings.cognee_base_url is not None
    assert settings.cognee_api_key is not None
    memory = CogneeCloudAdapter(
        base_url=settings.cognee_base_url,
        api_key=settings.cognee_api_key.get_secret_value(),
    )
    payload = EvidencePayload(
        data_id=DATA_ID,
        name="recallops-live-contract.txt",
        content=(
            "RecallOps contract marker 2026-06-28: amber-orbit-731. "
            "This contract-only item exists only for the gated adapter test."
        ),
        dataset=DATASET,
    )

    remembered_data_id: str | None = None
    try:
        remembered = await memory.remember_evidence(payload)
        assert remembered.status in {"completed", "running"}
        assert remembered.data_id is not None
        remembered_data_id = remembered.data_id

        request = RecallRequest(
            query="Which RecallOps contract marker mentions amber-orbit-731?",
            dataset=DATASET,
            session_id="incident:contract-probe",
            include_trace=True,
        )
        recalled = await _recall_until_document_state(
            memory,
            request,
            document_name=payload.name,
            present=True,
        )
        assert any(
            reference.document_name == payload.name
            for entry in recalled
            for reference in entry.references
        )

        forgotten = await memory.forget_evidence_item(
            DATASET,
            remembered_data_id,
        )
        assert forgotten.status == "deleted"
        remembered_data_id = None
        after = await _recall_until_document_state(
            memory,
            request,
            document_name=payload.name,
            present=False,
        )
        assert all(
            reference.document_name != payload.name
            for entry in after
            for reference in entry.references
        )
    finally:
        if remembered_data_id is not None:
            await memory.forget_evidence_item(DATASET, remembered_data_id)
        client = memory._client
        session = getattr(client, "_session", None) if client is not None else None
        if session is not None and not session.closed:
            await session.close()
