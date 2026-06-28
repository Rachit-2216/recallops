from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from recallops.db import Base
from recallops.domain.models import EvidenceItem, Incident
from recallops.memory.fake import FakeCogneeAdapter
from recallops.services.demo import DemoService

FIXTURES = Path(__file__).parents[3] / "demo" / "fixtures"
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


@pytest.mark.asyncio
async def test_seed_is_idempotent_with_stable_fixture_ids(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    service = DemoService(
        session=session,
        memory=memory,
        fixtures_dir=FIXTURES,
        dataset=DATASET,
    )

    first = await service.seed()
    first_ids = set(
        await session.scalars(select(EvidenceItem.data_id)),
    )
    second = await service.seed()
    second_ids = set(
        await session.scalars(select(EvidenceItem.data_id)),
    )

    assert first.seeded == 6
    assert first.reused == 0
    assert first.failed == 0
    assert first.ready is True
    assert second.seeded == 0
    assert second.reused == 6
    assert first_ids == second_ids
    assert len(first_ids) == 6
    assert memory.operation_counts["remember"] == 6


@pytest.mark.asyncio
async def test_reset_restores_demo_without_forgetting_unrelated_evidence(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    unrelated = EvidenceItem(
        data_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        dataset=DATASET,
        name="unrelated.md",
        kind="note",
        status="ready",
        content_hash="sha256:unrelated",
    )
    session.add(unrelated)
    await session.commit()
    service = DemoService(
        session=session,
        memory=memory,
        fixtures_dir=FIXTURES,
        dataset=DATASET,
    )

    result = await service.reset()
    await service.reset()

    assert result.incident_id == "INC-2048"
    assert await session.get(Incident, "INC-2048") is not None
    assert await session.get(EvidenceItem, unrelated.data_id) is not None
    incident_count = await session.scalar(select(func.count()).select_from(Incident))
    assert incident_count == 1
    assert memory.operation_counts["forget"] == 0


def test_fixture_data_id_uses_approved_uuid5_namespace() -> None:
    assert DemoService.fixture_data_id("postmortem-inc-1842.md") == (
        "e720a10a-eea4-5cca-b747-faac6b1ad7c8"
    )
