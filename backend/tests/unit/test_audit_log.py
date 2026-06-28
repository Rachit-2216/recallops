from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from recallops.db import Base
from recallops.repositories.audit import AuditRepository


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_audit_record_contains_safe_operation_context(
    session: AsyncSession,
) -> None:
    repository = AuditRepository(session)
    started_at = datetime(2026, 6, 28, 8, 10, tzinfo=UTC)
    operation = await repository.start(
        request_id="11111111-1111-4111-8111-111111111111",
        incident_id="INC-2048",
        trace_id="22222222-2222-4222-8222-222222222222",
        operation="recall",
        dataset="recallops_evidence_v1",
        target_id="incident:INC-2048",
        estimated_tokens=20_000,
        started_at=started_at,
    )

    await repository.finish(
        operation,
        success=True,
        finished_at=started_at + timedelta(milliseconds=125),
    )
    await session.commit()

    assert operation.request_id == "11111111-1111-4111-8111-111111111111"
    assert operation.incident_id == "INC-2048"
    assert operation.trace_id == "22222222-2222-4222-8222-222222222222"
    assert operation.operation == "recall"
    assert operation.dataset == "recallops_evidence_v1"
    assert operation.target_id == "incident:INC-2048"
    assert operation.duration_ms == 125
    assert operation.success is True
    assert operation.error_category is None
    assert operation.estimated_tokens == 20_000


@pytest.mark.asyncio
async def test_key_like_error_detail_is_fully_redacted(
    session: AsyncSession,
) -> None:
    repository = AuditRepository(session)
    operation = await repository.start(
        request_id="33333333-3333-4333-8333-333333333333",
        incident_id=None,
        trace_id=None,
        operation="remember",
        dataset="recallops_evidence_v1",
        target_id="fixture",
        estimated_tokens=250_000,
    )

    await repository.finish(
        operation,
        success=False,
        error_detail="COGNEE_API_KEY" + "=top-secret",
    )

    assert operation.error_category == "[REDACTED]"
