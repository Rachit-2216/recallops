import os

import pytest

from recallops.config import Settings
from recallops.memory.cognee_cloud import CogneeCloudAdapter
from recallops.memory.contract import EvidencePayload, RecallRequest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_COGNEE_INTEGRATION") != "1",
        reason="live Cognee integration is opt-in",
    ),
]

DATASET = "recallops_evidence_v1"
DATA_ID = "d1d38b21-e5e8-59d3-aa7f-613a16fa960d"


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
            "This synthetic item exists only for the gated adapter test."
        ),
        dataset=DATASET,
    )

    remembered = await memory.remember_evidence(payload)
    assert remembered.status in {"completed", "running"}

    request = RecallRequest(
        query="Which RecallOps contract marker mentions amber-orbit-731?",
        dataset=DATASET,
        session_id="incident:contract-probe",
        include_trace=True,
    )
    recalled = await memory.recall(request)
    assert any(
        reference.document_name == payload.name
        for entry in recalled
        for reference in entry.references
    )

    forgotten = await memory.forget_evidence_item(DATASET, DATA_ID)
    assert forgotten.status == "deleted"
    after = await memory.recall(request)
    assert all(
        reference.data_id != DATA_ID
        for entry in after
        for reference in entry.references
    )
