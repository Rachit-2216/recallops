from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from recallops.db import Base
from recallops.domain.models import (
    EvidenceItem,
    Feedback,
    Incident,
    RecallReference,
    RecallTrace,
)
from recallops.memory.contract import RecallRequest
from recallops.memory.fake import FakeCogneeAdapter
from recallops.repositories.audit import AuditRepository
from recallops.services.lifecycle import (
    MemoryLifecycleService,
    ResolutionValidationError,
)

DATASET = "recallops_evidence_v1"


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


async def _seed_referenced_trace(
    session: AsyncSession,
) -> tuple[Incident, RecallTrace]:
    incident = Incident(
        id="INC-2048",
        title="Checkout outage",
        severity="SEV1",
        service="checkout-api",
        status="active",
        session_id="incident:INC-2048",
        started_at=datetime.now(UTC),
    )
    evidence = EvidenceItem(
        data_id="11111111-1111-4111-8111-111111111111",
        dataset=DATASET,
        name="postmortem-inc-1842.md",
        kind="postmortem",
        status="ready",
        content_hash="sha256:postmortem",
    )
    trace = RecallTrace(
        incident_id=incident.id,
        query="How is deploy-418 related to Redis?",
        source="graph",
        search_type="GRAPH_COMPLETION_CONTEXT_EXTENSION",
        answer="INC-1842 had the same Redis TTL mismatch.",
        verification_state="referenced",
        latency_ms=12,
    )
    session.add_all([incident, evidence, trace])
    await session.flush()
    session.add(
        RecallReference(
            trace_id=trace.id,
            data_id=evidence.data_id,
            chunk_id="chunk-1",
            document_name=evidence.name,
            snippet="TTL units were not converted.",
        ),
    )
    await session.commit()
    return incident, trace


def _service(
    session: AsyncSession,
    memory: FakeCogneeAdapter,
) -> MemoryLifecycleService:
    return MemoryLifecycleService(
        session=session,
        memory=memory,
        audit=AuditRepository(session),
        dataset=DATASET,
    )


@pytest.mark.asyncio
async def test_feedback_is_stored_and_added_to_session_memory(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    incident, trace = await _seed_referenced_trace(session)

    feedback = await _service(session, memory).record_feedback(
        incident=incident,
        trace_id=trace.id,
        score=1,
        explanation="The Redis relationship and cited postmortem were correct.",
    )

    count = await session.scalar(select(func.count()).select_from(Feedback))
    assert feedback.trace_id == trace.id
    assert count == 1
    assert "feedback score 1" in memory.observations[incident.session_id][0]


@pytest.mark.asyncio
async def test_resolution_requires_human_confirmation_and_referenced_trace(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    incident, trace = await _seed_referenced_trace(session)
    service = _service(session, memory)

    with pytest.raises(ResolutionValidationError, match="human"):
        await service.resolve_incident(
            incident=incident,
            root_cause="TTL units were not converted.",
            mitigation="Rolled back TTL configuration.",
            verification="Checkout p95 recovered.",
            trace_ids=[trace.id],
            confirmed_by_human=False,
            request_id="11111111-1111-4111-8111-111111111111",
        )

    trace.verification_state = "unverified"
    await session.commit()
    with pytest.raises(ResolutionValidationError, match="referenced"):
        await service.resolve_incident(
            incident=incident,
            root_cause="TTL units were not converted.",
            mitigation="Rolled back TTL configuration.",
            verification="Checkout p95 recovered.",
            trace_ids=[trace.id],
            confirmed_by_human=True,
            request_id="22222222-2222-4222-8222-222222222222",
        )


@pytest.mark.asyncio
async def test_improve_failure_preserves_resolution_without_false_success(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter(fail_operations={"improve"})
    incident, trace = await _seed_referenced_trace(session)

    resolution = await _service(session, memory).resolve_incident(
        incident=incident,
        root_cause="deploy-418 passed milliseconds to a seconds adapter.",
        mitigation="Rolled back TTL configuration and reissued affected sessions.",
        verification="Checkout p95 and Redis misses returned to baseline.",
        trace_ids=[trace.id],
        confirmed_by_human=True,
        request_id="33333333-3333-4333-8333-333333333333",
    )

    assert resolution.promotion_state == "promotion_failed"
    assert incident.status == "mitigated"
    assert incident.resolved_at is None


@pytest.mark.asyncio
async def test_verified_resolution_is_recalled_from_clean_session(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    incident, trace = await _seed_referenced_trace(session)

    resolution = await _service(session, memory).resolve_incident(
        incident=incident,
        root_cause="deploy-418 passed milliseconds to a seconds adapter.",
        mitigation="Rolled back the TTL configuration and reissued affected sessions.",
        verification="Checkout p95 and Redis misses returned to baseline.",
        trace_ids=[trace.id],
        confirmed_by_human=True,
        request_id="44444444-4444-4444-8444-444444444444",
    )
    recalled = await memory.recall(
        RecallRequest(
            query="What verified mitigation fixed INC-2048?",
            dataset=DATASET,
            session_id="incident:INC-2099",
        ),
    )

    assert resolution.promotion_state == "promoted"
    assert incident.status == "resolved"
    assert "TTL configuration" in recalled[0].answer
    assert "reissued affected sessions" in recalled[0].answer
    assert recalled[0].source == "graph"
    assert recalled[0].references[0].document_name == (
        "verified-resolution-inc-2048.md"
    )
    promoted_item = await session.get(
        EvidenceItem,
        recalled[0].references[0].data_id,
    )
    assert promoted_item is not None
    assert promoted_item.kind == "memory_candidate"
