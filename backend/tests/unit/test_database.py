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
from recallops.domain.models import EvidenceItem, Incident

DEMO_START = datetime(2026, 6, 28, 8, 10, tzinfo=UTC)
STALE_DATA_ID = "43e633d0-bbed-5a2e-bf4e-c52f62c60f11"
INITIAL_TABLES = {
    "incidents",
    "evidence_items",
    "observations",
    "memory_candidates",
    "recall_traces",
    "recall_references",
    "feedback",
    "resolutions",
    "memory_operations",
    "credit_ledger",
}


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
async def test_initial_schema_persists_incident_and_evidence(
    session: AsyncSession,
) -> None:
    incident = Incident(
        id="INC-2048",
        title="Checkout outage",
        severity="SEV1",
        service="checkout-api",
        status="active",
        session_id="incident:INC-2048",
        started_at=DEMO_START,
    )
    evidence = EvidenceItem(
        data_id=STALE_DATA_ID,
        dataset="recallops_evidence_v1",
        name="stale-cache-reset-rule.md",
        kind="runbook",
        status="ready",
        content_hash="sha256:fixture",
    )
    session.add_all([incident, evidence])
    await session.commit()

    assert await session.get(Incident, "INC-2048") is not None
    assert await session.get(EvidenceItem, STALE_DATA_ID) is not None


def test_initial_metadata_contains_every_required_table() -> None:
    assert set(Base.metadata.tables) == INITIAL_TABLES
