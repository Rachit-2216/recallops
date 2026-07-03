import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from recallops.config import Settings
from recallops.db import Base
from recallops.main import create_app
from recallops.memory.contract import DatasetStatus
from recallops.memory.fake import FakeCogneeAdapter

FIXTURES = Path(__file__).parents[3] / "demo" / "fixtures"
ADMIN_HEADERS = {"X-Demo-Admin-Token": "test-demo-token"}
INCIDENT_ID = "CF-OUTAGE-2025-12-05"
QUERY = "How is the December 5 outage related to the November 18 outage?"


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
        assert (
            client.post(
                "/api/demo/seed",
                headers=ADMIN_HEADERS,
            ).status_code
            == 200
        )
        yield client, memory
    asyncio.run(engine.dispose())


def test_relationship_recall_returns_persisted_references(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory

    response = client.post(
        f"/api/incidents/{INCIDENT_ID}/recall",
        json={"query": QUERY, "include_trace": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert "November 18" in body["answer"]
    assert body["verification"] == "referenced"
    assert body["source"] == "graph"
    assert body["search_type"] == "GRAPH_COMPLETION_CONTEXT_EXTENSION"
    assert len(body["why_recalled"]) == 4
    assert any(
        reference["document_name"] == "cloudflare-november-18-postmortem.md"
        for reference in body["references"]
    )

    trace = client.get(
        f"/api/incidents/{INCIDENT_ID}/recalls/{body['trace_id']}",
    )
    assert trace.status_code == 200
    assert trace.json()["trace_id"] == body["trace_id"]
    assert trace.json()["references"] == body["references"]


def test_no_result_is_explicit_and_unverified(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory

    response = client.post(
        f"/api/incidents/{INCIDENT_ID}/recall",
        json={"query": "xylophonic quasar topology"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] is None
    assert response.json()["verification"] == "unverified"
    assert response.json()["no_result"] is True


def test_provider_failure_returns_safe_503(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, memory = client_and_memory
    memory.fail_operations.add("recall")

    response = client.post(
        f"/api/incidents/{INCIDENT_ID}/recall",
        json={"query": QUERY},
    )

    assert response.status_code == 503
    assert "api_key" not in response.text.casefold()
    assert "traceback" not in response.text.casefold()


def test_indexing_dataset_returns_partial_memory_202(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, memory = client_and_memory

    async def indexing(dataset: str) -> DatasetStatus:
        return DatasetStatus(dataset=dataset, ready=False, status="processing")

    memory.dataset_status = indexing  # type: ignore[method-assign]
    response = client.post(
        f"/api/incidents/{INCIDENT_ID}/recall",
        json={"query": QUERY},
    )

    assert response.status_code == 202
    assert response.json()["partial_memory"] is True
