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
ADMIN_HEADERS = {"X-Demo-Admin-Token": "test-demo-token"}
RELATIONSHIP_QUERY = "How is deploy-418 related to the previous Redis incident?"
RESOLUTION = {
    "root_cause": "deploy-418 passed millisecond TTL values to a seconds-based adapter.",
    "mitigation": "Rolled back the TTL configuration and reissued affected sessions.",
    "verification": "Checkout p95 and Redis session misses returned to baseline.",
    "confirmed_by_human": True,
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
        Settings(
            database_url=database_url,
            demo_admin_token="test-demo-token",
            _env_file=None,
        ),
        session_factory=session_factory,
        memory=memory,
        fixtures_dir=FIXTURES,
    )

    with TestClient(app) as client:
        assert client.post("/api/demo/reset").status_code == 200
        assert client.post(
            "/api/demo/seed",
            headers=ADMIN_HEADERS,
        ).status_code == 200
        yield client, memory
    asyncio.run(engine.dispose())


def _referenced_trace(client: TestClient) -> str:
    response = client.post(
        "/api/incidents/INC-2048/recall",
        json={"query": RELATIONSHIP_QUERY},
    )
    assert response.status_code == 200
    return response.json()["trace_id"]


def test_feedback_is_validated_and_stored(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    trace_id = _referenced_trace(client)

    response = client.post(
        "/api/incidents/INC-2048/feedback",
        json={
            "trace_id": trace_id,
            "score": 1,
            "explanation": "The Redis relationship and cited postmortem were correct.",
        },
    )

    assert response.status_code == 201
    assert response.json()["trace_id"] == trace_id
    assert response.json()["score"] == 1


def test_resolution_rejects_missing_human_confirmation(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    trace_id = _referenced_trace(client)

    response = client.post(
        "/api/incidents/INC-2048/resolve",
        json={
            **RESOLUTION,
            "trace_ids": [trace_id],
            "confirmed_by_human": False,
        },
    )

    assert response.status_code == 422


def test_resolution_promotes_and_clean_incident_recalls_verified_fix(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    trace_id = _referenced_trace(client)

    resolved = client.post(
        "/api/incidents/INC-2048/resolve",
        json={**RESOLUTION, "trace_ids": [trace_id]},
    )
    created = client.post(
        "/api/incidents",
        json={
            "id": "INC-2099",
            "title": "Clean proof incident",
            "severity": "SEV3",
            "service": "checkout-api",
        },
    )
    proof = client.post(
        "/api/incidents/INC-2099/recall",
        json={"query": "What verified mitigation fixed INC-2048?"},
    )

    assert resolved.status_code == 200
    assert resolved.json()["promotion_state"] == "promoted"
    assert resolved.json()["incident_status"] == "resolved"
    assert created.status_code == 201
    assert proof.status_code == 200
    assert "reissued affected sessions" in proof.json()["answer"]
    assert proof.json()["source"] == "graph"


def test_improve_failure_returns_retryable_stored_state(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, memory = client_and_memory
    trace_id = _referenced_trace(client)
    memory.fail_operations.add("improve")

    response = client.post(
        "/api/incidents/INC-2048/resolve",
        json={**RESOLUTION, "trace_ids": [trace_id]},
    )
    detail = client.get("/api/incidents/INC-2048")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MEMORY_PROVIDER_UNAVAILABLE"
    assert detail.json()["resolution"]["promotion_state"] == "promotion_failed"
