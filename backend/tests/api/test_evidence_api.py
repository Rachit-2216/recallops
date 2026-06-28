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
from recallops.services.demo import DemoService

FIXTURES = Path(__file__).parents[3] / "demo" / "fixtures"
ADMIN_HEADERS = {"X-Demo-Admin-Token": "test-demo-token"}
STALE_ID = DemoService.fixture_data_id("stale-cache-reset-rule.md")


@pytest.fixture
def client() -> Iterator[TestClient]:
    database_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(database_url)

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app(
        Settings(
            database_url=database_url,
            demo_admin_token="test-demo-token",
            _env_file=None,
        ),
        session_factory=session_factory,
        memory=FakeCogneeAdapter(),
        fixtures_dir=FIXTURES,
    )
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(engine.dispose())


def _seed(client: TestClient) -> None:
    response = client.post("/api/demo/seed", headers=ADMIN_HEADERS)
    assert response.status_code == 200


def test_lists_seeded_evidence_and_reports_item_status(
    client: TestClient,
) -> None:
    _seed(client)

    listed = client.get("/api/evidence")
    detail = client.get(f"/api/evidence/{STALE_ID}")
    status = client.get(f"/api/evidence/{STALE_ID}/status")

    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 6
    assert detail.status_code == 200
    assert detail.json()["name"] == "stale-cache-reset-rule.md"
    assert detail.json()["is_stale"] is True
    assert status.json() == {
        "data_id": STALE_ID,
        "local_status": "ready",
        "memory_status": "ready",
    }


def test_uploads_supported_local_evidence_and_reuses_identical_content(
    client: TestClient,
) -> None:
    upload = {
        "file": (
            "operator-note.md",
            b"Synthetic operator note.",
            "text/markdown",
        ),
    }

    first = client.post("/api/evidence", files=upload)
    second = client.post("/api/evidence", files=upload)

    assert first.status_code == 201
    assert first.json()["status"] == "ready"
    assert first.json()["reused"] is False
    assert second.status_code == 200
    assert second.json()["data_id"] == first.json()["data_id"]
    assert second.json()["reused"] is True


def test_upload_rejects_unsupported_type(client: TestClient) -> None:
    response = client.post(
        "/api/evidence",
        files={"file": ("payload.exe", b"not executable", "application/octet-stream")},
    )

    assert response.status_code == 415


def test_forget_requires_exact_confirmation(client: TestClient) -> None:
    _seed(client)

    response = client.request(
        "DELETE",
        f"/api/evidence/{STALE_ID}",
        json={
            "confirmation": "forget stale-cache-reset-rule.md",
            "verification_query": '"flush all Redis cache"',
        },
    )

    assert response.status_code == 422


def test_forget_returns_before_and_after_retrieval_proof(
    client: TestClient,
) -> None:
    _seed(client)

    response = client.request(
        "DELETE",
        f"/api/evidence/{STALE_ID}",
        json={
            "confirmation": "FORGET stale-cache-reset-rule.md",
            "verification_query": '"flush all Redis cache"',
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "data_id": STALE_ID,
        "status": "forgotten",
        "before_reference_found": True,
        "after_reference_found": False,
    }
    detail = client.get(f"/api/evidence/{STALE_ID}")
    assert detail.json()["status"] == "forgotten"


def test_missing_evidence_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/evidence/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    )

    assert response.status_code == 404
