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


@pytest.fixture
def client() -> Iterator[TestClient]:
    database_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(database_url)

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        database_url=database_url,
        demo_admin_token="test-demo-token",
        _env_file=None,
    )
    app = create_app(
        settings,
        session_factory=session_factory,
        memory=FakeCogneeAdapter(),
        fixtures_dir=FIXTURES,
    )

    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(engine.dispose())


def test_reset_restores_the_public_case_study(client: TestClient) -> None:
    response = client.post("/api/demo/reset")

    assert response.status_code == 200
    assert response.json() == {
        "incident_id": "CF-OUTAGE-2025-12-05",
        "observation_count": 3,
        "candidate_count": 1,
        "case_study": "public_postmortem",
    }


@pytest.mark.parametrize("token", [None, "incorrect-token"])
def test_seed_requires_one_opaque_admin_token(
    client: TestClient,
    token: str | None,
) -> None:
    headers = {} if token is None else {"X-Demo-Admin-Token": token}

    response = client.post("/api/demo/seed", headers=headers)

    assert response.status_code == 401
    assert "incorrect" not in response.text.lower()
    assert "expected" not in response.text.lower()


def test_seed_endpoint_is_idempotent(client: TestClient) -> None:
    headers = {"X-Demo-Admin-Token": "test-demo-token"}

    first = client.post("/api/demo/seed", headers=headers)
    second = client.post("/api/demo/seed", headers=headers)

    assert first.status_code == 200
    assert first.json() == {
        "dataset": "recallops_evidence_v1",
        "seeded": 6,
        "reused": 0,
        "failed": 0,
        "ready": True,
    }
    assert second.status_code == 200
    assert second.json()["seeded"] == 0
    assert second.json()["reused"] == 6
