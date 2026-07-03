from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from recallops.db import Base
from recallops.domain.models import EvidenceItem, MemoryOperation
from recallops.memory.contract import (
    EvidencePayload,
    ForgetReceipt,
)
from recallops.memory.fake import FakeCogneeAdapter
from recallops.repositories.audit import AuditRepository
from recallops.services.lifecycle import (
    ForgetConfirmationMismatch,
    ForgetVerificationFailed,
    MemoryLifecycleService,
    MemoryStateConflict,
)

DATASET = "recallops_evidence_v1"
STALE_ID = "43e633d0-bbed-5a2e-bf4e-c52f62c60f11"


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


async def _ready_stale_item(
    session: AsyncSession,
    memory: FakeCogneeAdapter,
) -> EvidenceItem:
    item = EvidenceItem(
        data_id=STALE_ID,
        dataset=DATASET,
        name="unsafe-global-killswitch-assumption.md",
        kind="runbook",
        status="ready",
        content_hash="sha256:stale",
        is_stale=True,
    )
    session.add(item)
    await session.commit()
    await memory.remember_evidence(
        EvidencePayload(
            data_id=STALE_ID,
            dataset=DATASET,
            name=item.name,
            content="Any WAF rule can be disabled through the global killswitch.",
        ),
    )
    return item


@pytest.mark.asyncio
async def test_forget_succeeds_only_after_recall_proves_absence(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    item = await _ready_stale_item(session, memory)
    service = MemoryLifecycleService(
        session=session,
        memory=memory,
        audit=AuditRepository(session),
    )

    result = await service.forget_evidence(
        item=item,
        confirmation="FORGET unsafe-global-killswitch-assumption.md",
        verification_query='"Any WAF rule can be disabled"',
        request_id="11111111-1111-4111-8111-111111111111",
    )

    assert result.before_reference_found is True
    assert result.after_reference_found is False
    assert item.status == "forgotten"
    assert item.forgotten_at is not None


@pytest.mark.asyncio
async def test_forget_requires_exact_confirmation(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    item = await _ready_stale_item(session, memory)
    service = MemoryLifecycleService(
        session=session,
        memory=memory,
        audit=AuditRepository(session),
    )

    with pytest.raises(ForgetConfirmationMismatch):
        await service.forget_evidence(
            item=item,
            confirmation="forget unsafe-global-killswitch-assumption.md",
            verification_query='"Any WAF rule can be disabled"',
            request_id="22222222-2222-4222-8222-222222222222",
        )

    assert memory.operation_counts["forget"] == 0
    assert item.status == "ready"


@pytest.mark.asyncio
async def test_forget_rejects_non_ready_evidence(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    item = await _ready_stale_item(session, memory)
    item.status = "processing"
    service = MemoryLifecycleService(
        session=session,
        memory=memory,
        audit=AuditRepository(session),
    )

    with pytest.raises(MemoryStateConflict, match="ready"):
        await service.forget_evidence(
            item=item,
            confirmation="FORGET unsafe-global-killswitch-assumption.md",
            verification_query='"Any WAF rule can be disabled"',
            request_id="33333333-3333-4333-8333-333333333333",
        )


class StickyForgetFake(FakeCogneeAdapter):
    async def forget_evidence_item(
        self,
        dataset: str,
        data_id: str,
    ) -> ForgetReceipt:
        self.operation_counts["forget"] += 1
        return ForgetReceipt(status="deleted", data_id=data_id)


@pytest.mark.asyncio
async def test_failed_absence_verification_keeps_item_visible_and_audits_failure(
    session: AsyncSession,
) -> None:
    memory = StickyForgetFake()
    item = await _ready_stale_item(session, memory)
    service = MemoryLifecycleService(
        session=session,
        memory=memory,
        audit=AuditRepository(session),
    )

    with pytest.raises(ForgetVerificationFailed):
        await service.forget_evidence(
            item=item,
            confirmation="FORGET unsafe-global-killswitch-assumption.md",
            verification_query='"Any WAF rule can be disabled"',
            request_id="44444444-4444-4444-8444-444444444444",
        )

    operation = await session.scalar(
        select(MemoryOperation).order_by(MemoryOperation.started_at.desc()),
    )
    assert item.status == "ready"
    assert operation is not None
    assert operation.success is False
    assert operation.error_category == "forget_verification_failed"
