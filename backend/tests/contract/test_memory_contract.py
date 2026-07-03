import pytest

from recallops.memory.contract import (
    CogneeMemoryPort,
    EvidencePayload,
    RecallRequest,
)
from recallops.memory.fake import FakeCogneeAdapter, FakeMemoryError

DATA_ID = "11111111-1111-4111-8111-111111111111"
DATASET = "recallops_evidence_v1"
INCIDENT_ID = "CF-OUTAGE-2025-12-05"
SESSION_ID = f"incident:{INCIDENT_ID}"


async def exercise_memory_contract(memory: CogneeMemoryPort) -> None:
    receipt = await memory.remember_evidence(
        EvidencePayload(
            data_id=DATA_ID,
            name="cloudflare-november-18-postmortem.md",
            content="The November 18 outage involved global configuration propagation.",
            dataset=DATASET,
        ),
    )
    assert receipt.status == "completed"

    observation = await memory.remember_observation(
        session_id=SESSION_ID,
        content="A WAF configuration change propagated globally.",
    )
    assert observation.status == "completed"

    results = await memory.recall(
        RecallRequest(
            query="How is the December 5 outage related to November 18?",
            dataset=DATASET,
            session_id=SESSION_ID,
            include_trace=True,
        ),
    )
    assert results[0].references[0].document_name == ("cloudflare-november-18-postmortem.md")

    status = await memory.dataset_status(DATASET)
    assert status.ready is True
    health = await memory.health()
    assert health.reachable is True

    improved = await memory.improve_session(
        dataset=DATASET,
        session_ids=[SESSION_ID],
    )
    assert improved.status == "completed"

    forgotten = await memory.forget_evidence_item(
        dataset=DATASET,
        data_id=DATA_ID,
    )
    assert forgotten.status == "deleted"


@pytest.mark.asyncio
async def test_fake_adapter_satisfies_memory_contract() -> None:
    await exercise_memory_contract(FakeCogneeAdapter())


@pytest.mark.asyncio
async def test_fake_forget_removes_only_the_target_reference() -> None:
    memory = FakeCogneeAdapter()
    await memory.remember_evidence(
        EvidencePayload(
            data_id=DATA_ID,
            name="cloudflare-november-18-postmortem.md",
            content="November 18 exposed global configuration blast radius.",
            dataset=DATASET,
        ),
    )
    stale_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    await memory.remember_evidence(
        EvidencePayload(
            data_id=stale_id,
            name="unsafe-global-killswitch-assumption.md",
            content="Any WAF rule can be disabled through the global killswitch.",
            dataset=DATASET,
        ),
    )
    request = RecallRequest(
        query="How is the December 5 outage related to November 18?",
        dataset=DATASET,
        session_id=SESSION_ID,
    )

    before = await memory.recall(request)
    assert {reference.document_name for reference in before[0].references} == {
        "cloudflare-november-18-postmortem.md",
        "unsafe-global-killswitch-assumption.md",
    }

    await memory.forget_evidence_item(DATASET, stale_id)
    after = await memory.recall(request)
    assert {reference.document_name for reference in after[0].references} == {
        "cloudflare-november-18-postmortem.md",
    }


@pytest.mark.asyncio
async def test_fake_improve_bridges_verified_resolution_to_clean_session() -> None:
    memory = FakeCogneeAdapter()
    await memory.remember_observation(
        SESSION_ID,
        (
            f"Verified resolution for {INCIDENT_ID}: used a controlled rollout, "
            "rolled back the configuration, and restored traffic by 09:12 UTC."
        ),
    )

    await memory.improve_session(DATASET, [SESSION_ID])
    results = await memory.recall(
        RecallRequest(
            query=f"What verified mitigation fixed {INCIDENT_ID}?",
            dataset=DATASET,
            session_id=f"incident:{INCIDENT_ID}-proof",
        ),
    )

    assert "controlled rollout" in results[0].answer
    assert "09:12 UTC" in results[0].answer
    assert results[0].source == "graph"
    assert results[0].references[0].document_name == ("verified-resolution-cf-outage-2025-12-05.md")


@pytest.mark.asyncio
async def test_fake_configurable_failures_are_counted() -> None:
    memory = FakeCogneeAdapter(fail_operations={"recall"})

    with pytest.raises(FakeMemoryError, match="recall"):
        await memory.recall(
            RecallRequest(
                query="What happened?",
                dataset=DATASET,
                session_id=SESSION_ID,
            ),
        )

    assert memory.operation_counts["recall"] == 1
