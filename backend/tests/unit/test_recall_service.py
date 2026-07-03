from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from recallops.db import Base
from recallops.domain.enums import VerificationState
from recallops.domain.models import EvidenceItem, Incident
from recallops.memory.contract import (
    EvidencePayload,
    RecallEntry,
    RecallReference,
)
from recallops.memory.fake import FakeCogneeAdapter
from recallops.repositories.audit import AuditRepository
from recallops.repositories.recalls import RecallRepository
from recallops.services.credit_guard import CreditGuard
from recallops.services.recall import (
    MemoryProviderUnavailable,
    RecallService,
    is_trace_eligible,
    verification_for,
)

DATASET = "recallops_evidence_v1"
POSTMORTEM_ID = "11111111-1111-4111-8111-111111111111"


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


def test_verification_policy_requires_references_and_honors_contradiction() -> None:
    reference = RecallReference(
        data_id=POSTMORTEM_ID,
        chunk_id="chunk-1",
        document_name="cloudflare-november-18-postmortem.md",
        snippet="A global configuration artifact propagated without rollout gates.",
    )
    entries_with_reference = [
        RecallEntry(
            answer="Referenced",
            source="graph",
            search_type="GRAPH",
            references=(reference,),
        ),
    ]
    entries_without_reference = [
        RecallEntry(
            answer="Unsupported",
            source="graph",
            search_type="GRAPH",
        ),
    ]
    entries_with_contradiction = [
        RecallEntry(
            answer="Payment gateway metrics contradict the hypothesis.",
            source="contradiction",
            search_type="GRAPH",
            references=(reference,),
        ),
    ]

    assert verification_for(entries_with_reference) == VerificationState.REFERENCED
    assert verification_for(entries_without_reference) == VerificationState.UNVERIFIED
    assert verification_for(entries_with_contradiction) == VerificationState.CONTRADICTED
    assert not is_trace_eligible(VerificationState.UNVERIFIED)


async def _seed_incident_and_evidence(
    session: AsyncSession,
    memory: FakeCogneeAdapter,
) -> Incident:
    incident = Incident(
        id="CF-OUTAGE-2025-12-05",
        title="Cloudflare HTTP 500 outage",
        severity="SEV1",
        service="Cloudflare FL1 proxy",
        status="active",
        session_id="incident:CF-OUTAGE-2025-12-05",
        started_at=datetime.now(UTC),
    )
    evidence = EvidenceItem(
        data_id=POSTMORTEM_ID,
        dataset=DATASET,
        name="cloudflare-november-18-postmortem.md",
        kind="postmortem",
        status="ready",
        content_hash="sha256:postmortem",
    )
    session.add_all([incident, evidence])
    await session.commit()
    await memory.remember_evidence(
        EvidencePayload(
            data_id=POSTMORTEM_ID,
            name=evidence.name,
            content=(
                "The November 18 outage also followed rapid global configuration propagation."
            ),
            dataset=DATASET,
        ),
    )
    return incident


def _service(
    session: AsyncSession,
    memory: FakeCogneeAdapter,
) -> RecallService:
    return RecallService(
        session=session,
        memory=memory,
        repository=RecallRepository(session),
        audit=AuditRepository(session),
        credit_guard=CreditGuard(
            supply=14_000_000,
            protected_reserve=6_000_000,
        ),
        dataset=DATASET,
    )


@pytest.mark.asyncio
async def test_recall_persists_referenced_trace_and_why_recalled(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    incident = await _seed_incident_and_evidence(session, memory)

    result = await _service(session, memory).ask(
        incident=incident,
        query="How is the December 5 outage related to the November 18 outage?",
        request_id="11111111-1111-4111-8111-111111111111",
    )

    persisted = await RecallRepository(session).get(result.trace_id)
    assert result.verification == VerificationState.REFERENCED
    assert result.source == "graph"
    assert result.search_type == "GRAPH_COMPLETION_CONTEXT_EXTENSION"
    assert len(result.why_recalled) == 4
    assert persisted is not None
    assert persisted.references[0].document_name == "cloudflare-november-18-postmortem.md"


@pytest.mark.asyncio
async def test_empty_recall_is_explicit_unverified_no_result(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    incident = await _seed_incident_and_evidence(session, memory)

    result = await _service(session, memory).ask(
        incident=incident,
        query="xylophonic quasar topology",
        request_id="22222222-2222-4222-8222-222222222222",
    )

    assert result.answer is None
    assert result.verification == VerificationState.UNVERIFIED
    assert result.no_result is True
    assert result.references == ()


@pytest.mark.asyncio
async def test_provider_failure_is_safe_and_typed(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter(fail_operations={"recall"})
    incident = await _seed_incident_and_evidence(session, memory)

    with pytest.raises(MemoryProviderUnavailable):
        await _service(session, memory).ask(
            incident=incident,
            query="How is the December 5 outage related to November 18?",
            request_id="33333333-3333-4333-8333-333333333333",
        )
