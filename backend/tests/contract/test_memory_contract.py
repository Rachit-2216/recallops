import pytest

from recallops.memory.contract import (
    CogneeMemoryPort,
    EvidencePayload,
    RecallRequest,
)
from recallops.memory.fake import FakeCogneeAdapter, FakeMemoryError

DATA_ID = "11111111-1111-4111-8111-111111111111"
DATASET = "recallops_evidence_v1"
SESSION_ID = "incident:INC-2048"


async def exercise_memory_contract(memory: CogneeMemoryPort) -> None:
    receipt = await memory.remember_evidence(
        EvidencePayload(
            data_id=DATA_ID,
            name="postmortem-inc-1842.md",
            content="INC-1842 was caused by a seconds-to-milliseconds TTL mismatch.",
            dataset=DATASET,
        ),
    )
    assert receipt.status == "completed"

    observation = await memory.remember_observation(
        session_id=SESSION_ID,
        content="Redis session misses rose after deploy-418.",
    )
    assert observation.status == "completed"

    results = await memory.recall(
        RecallRequest(
            query="How is deploy-418 related to the Redis incident?",
            dataset=DATASET,
            session_id=SESSION_ID,
            include_trace=True,
        ),
    )
    assert results[0].references[0].document_name == "postmortem-inc-1842.md"

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
            name="postmortem-inc-1842.md",
            content="INC-1842 documented the Redis TTL mismatch.",
            dataset=DATASET,
        ),
    )
    stale_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    await memory.remember_evidence(
        EvidencePayload(
            data_id=stale_id,
            name="stale-cache-reset-rule.md",
            content="Obsolete guidance: flush all Redis cache.",
            dataset=DATASET,
        ),
    )
    request = RecallRequest(
        query="How is deploy-418 related to the Redis incident?",
        dataset=DATASET,
        session_id=SESSION_ID,
    )

    before = await memory.recall(request)
    assert {reference.document_name for reference in before[0].references} == {
        "postmortem-inc-1842.md",
        "stale-cache-reset-rule.md",
    }

    await memory.forget_evidence_item(DATASET, stale_id)
    after = await memory.recall(request)
    assert {reference.document_name for reference in after[0].references} == {
        "postmortem-inc-1842.md",
    }


@pytest.mark.asyncio
async def test_fake_improve_bridges_verified_resolution_to_clean_session() -> None:
    memory = FakeCogneeAdapter()
    await memory.remember_observation(
        SESSION_ID,
        (
            "Verified resolution for INC-2048: rolled back the TTL configuration "
            "and reissued affected sessions."
        ),
    )

    await memory.improve_session(DATASET, [SESSION_ID])
    results = await memory.recall(
        RecallRequest(
            query="What verified mitigation fixed INC-2048?",
            dataset=DATASET,
            session_id="incident:INC-2048-proof",
        ),
    )

    assert "rolled back the TTL configuration" in results[0].answer
    assert "reissued affected sessions" in results[0].answer
    assert results[0].source == "graph"
    assert results[0].references[0].document_name == (
        "verified-resolution-inc-2048.md"
    )


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
