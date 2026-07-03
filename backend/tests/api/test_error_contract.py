import asyncio
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from recallops.config import Settings
from recallops.db import Base
from recallops.main import create_app
from recallops.memory.fake import FakeCogneeAdapter

FIXTURES = Path(__file__).parents[3] / "demo" / "fixtures"
INCIDENT = {
    "id": "INC-5001",
    "title": "Cloudflare HTTP 500 outage",
    "severity": "SEV1",
    "service": "Cloudflare FL1 proxy",
}


@pytest.fixture
def client_and_memory() -> Iterator[tuple[TestClient, FakeCogneeAdapter]]:
    database_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(database_url)

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    memory = FakeCogneeAdapter()
    app = create_app(
        Settings(
            database_url=database_url,
            demo_admin_token="opaque-test-token",
            _env_file=None,
        ),
        session_factory=async_sessionmaker(engine, expire_on_commit=False),
        memory=memory,
        fixtures_dir=FIXTURES,
    )
    with TestClient(app) as client:
        yield client, memory
    asyncio.run(engine.dispose())


def _assert_safe_error(
    response: object,
    *,
    status_code: int,
    code: str,
) -> None:
    assert hasattr(response, "status_code")
    assert response.status_code == status_code  # type: ignore[union-attr]
    payload = response.json()  # type: ignore[union-attr]
    assert set(payload) == {"error"}
    assert set(payload["error"]) == {
        "code",
        "message",
        "retryable",
        "request_id",
    }
    assert payload["error"]["code"] == code
    assert isinstance(payload["error"]["message"], str)
    assert isinstance(payload["error"]["retryable"], bool)
    UUID(payload["error"]["request_id"])
    serialized = response.text.casefold()  # type: ignore[union-attr]
    for forbidden in (
        "traceback",
        "api_key",
        "authorization",
        "http://",
        "https://",
        "headers",
    ):
        assert forbidden not in serialized


def test_401_uses_safe_error_envelope(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    response = client.post("/api/demo/seed")
    _assert_safe_error(response, status_code=401, code="UNAUTHORIZED")


def test_404_uses_safe_error_envelope(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    response = client.get("/api/incidents/INC-9999")
    _assert_safe_error(response, status_code=404, code="NOT_FOUND")


def test_409_uses_safe_error_envelope(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    assert client.post("/api/incidents", json=INCIDENT).status_code == 201
    response = client.post("/api/incidents", json=INCIDENT)
    _assert_safe_error(response, status_code=409, code="CONFLICT")


def test_413_uses_safe_error_envelope(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    response = client.post(
        "/api/evidence",
        files={"file": ("large.md", b"x" * (5 * 1024 * 1024 + 1), "text/markdown")},
    )
    _assert_safe_error(response, status_code=413, code="PAYLOAD_TOO_LARGE")


def test_415_uses_safe_error_envelope(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    response = client.post(
        "/api/evidence",
        files={"file": ("payload.exe", b"binary", "application/octet-stream")},
    )
    _assert_safe_error(response, status_code=415, code="UNSUPPORTED_MEDIA_TYPE")


def test_422_uses_safe_error_envelope(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    response = client.post("/api/incidents", json={"id": "bad"})
    _assert_safe_error(response, status_code=422, code="VALIDATION_ERROR")


def test_429_uses_safe_error_envelope(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, _ = client_and_memory
    assert client.post("/api/incidents", json=INCIDENT).status_code == 201
    for _ in range(20):
        assert (
            client.post(
                "/api/incidents/INC-5001/recall",
                json={"query": "no matching memory"},
                headers={"X-Demo-Session": "rate-limit-contract"},
            ).status_code
            == 200
        )
    response = client.post(
        "/api/incidents/INC-5001/recall",
        json={"query": "no matching memory"},
        headers={"X-Demo-Session": "rate-limit-contract"},
    )
    _assert_safe_error(response, status_code=429, code="RATE_LIMITED")


def test_503_uses_safe_retryable_memory_error(
    client_and_memory: tuple[TestClient, FakeCogneeAdapter],
) -> None:
    client, memory = client_and_memory
    assert client.post("/api/incidents", json=INCIDENT).status_code == 201
    memory.fail_operations.add("recall")
    response = client.post(
        "/api/incidents/INC-5001/recall",
        json={"query": "How is December 5 related to November 18?"},
    )
    _assert_safe_error(
        response,
        status_code=503,
        code="MEMORY_PROVIDER_UNAVAILABLE",
    )
    assert response.json()["error"]["retryable"] is True
