from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from recallops.db import Base
from recallops.domain.models import Observation
from recallops.memory.fake import FakeCogneeAdapter
from recallops.services.incidents import (
    DuplicateIncident,
    IncidentInputError,
    IncidentService,
)


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
@pytest.mark.parametrize(
    "incident_id",
    ["2048", "INC-", "INC-123456789", "inc-2048", "INC-12A"],
)
async def test_incident_id_must_match_locked_format(
    session: AsyncSession,
    incident_id: str,
) -> None:
    service = IncidentService(session=session, memory=FakeCogneeAdapter())

    with pytest.raises(IncidentInputError, match="INC-"):
        await service.create(
            incident_id=incident_id,
            title="Edge proxy outage",
            severity="SEV1",
            service="edge-proxy",
        )


@pytest.mark.asyncio
async def test_create_strips_fields_and_generates_session_id(
    session: AsyncSession,
) -> None:
    service = IncidentService(session=session, memory=FakeCogneeAdapter())

    incident = await service.create(
        incident_id="INC-5001",
        title="  Edge proxy outage  ",
        severity="SEV1",
        service="  edge-proxy ",
    )

    assert incident.title == "Edge proxy outage"
    assert incident.service == "edge-proxy"
    assert incident.session_id == "incident:INC-5001"
    assert incident.status == "active"


@pytest.mark.asyncio
async def test_duplicate_incident_is_rejected(session: AsyncSession) -> None:
    service = IncidentService(session=session, memory=FakeCogneeAdapter())
    values = {
        "incident_id": "INC-5001",
        "title": "Edge proxy outage",
        "severity": "SEV1",
        "service": "edge-proxy",
    }
    await service.create(**values)

    with pytest.raises(DuplicateIncident):
        await service.create(**values)


@pytest.mark.asyncio
async def test_observation_is_session_stored_when_memory_succeeds(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    service = IncidentService(session=session, memory=memory)
    await service.create(
        incident_id="INC-5001",
        title="Edge proxy outage",
        severity="SEV1",
        service="edge-proxy",
    )

    observation = await service.observe(
        incident_id="INC-5001",
        content="HTTP 500 errors rose after a WAF change.",
    )

    assert observation.memory_status == "session_stored"
    assert memory.observations["incident:INC-5001"] == [
        "HTTP 500 errors rose after a WAF change.",
    ]


@pytest.mark.asyncio
async def test_failed_observation_is_pending_and_retry_reuses_id(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter(fail_operations={"remember"})
    service = IncidentService(session=session, memory=memory)
    await service.create(
        incident_id="INC-5001",
        title="Edge proxy outage",
        severity="SEV1",
        service="edge-proxy",
    )
    pending = await service.observe(
        incident_id="INC-5001",
        content="HTTP 500 errors rose after a WAF change.",
    )
    assert pending.memory_status == "pending"
    memory.fail_operations.clear()

    retried = await service.observe(
        incident_id="INC-5001",
        content=pending.content,
        observation_id=pending.id,
    )

    count = await session.scalar(select(func.count()).select_from(Observation))
    assert pending.memory_status == "session_stored"
    assert retried.id == pending.id
    assert retried.memory_status == "session_stored"
    assert count == 1
