import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from recallops.config import Settings
from recallops.db import Base
from recallops.main import create_app
from recallops.memory.fake import FakeCogneeAdapter

FIXTURES = Path(__file__).parents[3] / "demo" / "fixtures"
INCIDENT = {
    "id": "INC-2048",
    "title": "Checkout outage",
    "severity": "SEV1",
    "service": "checkout-api",
}


@pytest.fixture
def client_and_memory() -> Iterator[tuple[TestClient, FakeCogneeAdapter]]:
    database_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(database_url)

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    memory = FakeCogneeAdapter()
    app = create_app(
        Settings(database_url=database_url, _env_file=None),
        session_factory=session_factory,
        memory=memory,
        fixtures_dir=FIXTURES,
    )
    with TestClient(app) as client:
        yield client, memory
    asyncio.run(engine.dispose())


def test_create_list_and_detail_incident(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory

    created = client.post("/api/incidents", json=INCIDENT)
    listed = client.get("/api/incidents")
    detail = client.get("/api/incidents/INC-2048")

    assert created.status_code == 201
    assert created.json()["session_id"] == "incident:INC-2048"
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == ["INC-2048"]
    assert detail.status_code == 200
    assert detail.json()["incident"]["status"] == "active"
    assert detail.json()["observations"] == []
    assert detail.json()["resolution"] is None
    assert "protected_reserve" in detail.json()["budget"]


def test_duplicate_incident_returns_conflict(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    assert client.post("/api/incidents", json=INCIDENT).status_code == 201

    response = client.post("/api/incidents", json=INCIDENT)

    assert response.status_code == 409


def test_client_cannot_supply_session_id(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory

    response = client.post(
        "/api/incidents",
        json={**INCIDENT, "session_id": "attacker-controlled"},
    )

    assert response.status_code == 422


def test_observation_is_saved_to_session_memory(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    client.post("/api/incidents", json=INCIDENT)

    response = client.post(
        "/api/incidents/INC-2048/observe",
        json={"content": "Redis misses rose after deploy-418."},
    )

    assert response.status_code == 200
    assert response.json()["memory_status"] == "session_stored"
    assert response.json()["memory_layer"] == "session"


def test_pending_observation_retry_reuses_the_same_id(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, memory = client_and_memory
    client.post("/api/incidents", json=INCIDENT)
    memory.fail_operations.add("remember")
    pending = client.post(
        "/api/incidents/INC-2048/observe",
        json={"content": "Redis misses rose after deploy-418."},
    )
    memory.fail_operations.clear()

    retried = client.post(
        "/api/incidents/INC-2048/observe",
        json={
            "content": "Redis misses rose after deploy-418.",
            "observation_id": pending.json()["id"],
        },
    )

    assert pending.status_code == 202
    assert pending.json()["memory_status"] == "pending"
    assert retried.status_code == 200
    assert retried.json()["id"] == pending.json()["id"]
    detail = client.get("/api/incidents/INC-2048").json()
    assert len(detail["observations"]) == 1
