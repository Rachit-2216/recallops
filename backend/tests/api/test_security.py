import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from recallops.config import Settings
from recallops.db import Base
from recallops.main import create_app
from recallops.memory.fake import FakeCogneeAdapter

ORIGIN = "https://recallops.example"


@pytest.fixture
def public_client() -> Iterator[TestClient]:
    database_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(database_url)

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    app = create_app(
        Settings(
            env="production",
            public_origin=ORIGIN,
            database_url=database_url,
            demo_mode=True,
            _env_file=None,
        ),
        session_factory=async_sessionmaker(engine, expire_on_commit=False),
        memory=FakeCogneeAdapter(),
    )
    with TestClient(app) as client:
        yield client
    asyncio.run(engine.dispose())


def test_cors_accepts_only_the_configured_origin(public_client: TestClient) -> None:
    accepted = public_client.options(
        "/api/health",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    rejected = public_client.options(
        "/api/health",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert accepted.headers["access-control-allow-origin"] == ORIGIN
    assert "access-control-allow-origin" not in rejected.headers


def test_security_headers_are_applied(public_client: TestClient) -> None:
    response = public_client.get("/api/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    policy = response.headers["content-security-policy"]
    assert "default-src 'self'" in policy
    assert "style-src 'self' 'unsafe-inline'" in policy
    assert "object-src 'none'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "unsafe-eval" not in policy


def test_public_demo_blocks_arbitrary_upload_and_url(
    public_client: TestClient,
) -> None:
    upload = public_client.post(
        "/api/evidence",
        files={"file": ("operator.md", b"private note", "text/markdown")},
    )
    url = public_client.post(
        "/api/evidence/url",
        json={"url": "https://example.com/operator.md"},
    )

    assert upload.status_code == 403
    assert url.status_code == 403


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "http://example.com/evidence.md",
        "file:///etc/passwd",
        "https://127.0.0.1/evidence.md",
        "https://10.0.0.4/evidence.md",
        "https://169.254.169.254/latest/meta-data",
        "https://localhost/evidence.md",
    ],
)
def test_local_url_mode_rejects_unsafe_destinations(unsafe_url: str) -> None:
    app = create_app(
        Settings(allow_url_ingestion=True, _env_file=None),
        memory=FakeCogneeAdapter(),
    )

    response = TestClient(app).post(
        "/api/evidence/url",
        json={"url": unsafe_url},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_excessive_recall_is_rate_limited(public_client: TestClient) -> None:
    incident = {
        "id": "INC-501",
        "title": "Rate limit contract",
        "severity": "SEV3",
        "service": "Cloudflare FL1 proxy",
    }
    assert public_client.post("/api/incidents", json=incident).status_code == 201
    for _ in range(20):
        response = public_client.post(
            "/api/incidents/INC-501/recall",
            json={"query": "no matching evidence"},
            headers={"X-Demo-Session": "security-rate-limit"},
        )
        assert response.status_code == 200

    blocked = public_client.post(
        "/api/incidents/INC-501/recall",
        json={"query": "no matching evidence"},
        headers={"X-Demo-Session": "security-rate-limit"},
    )

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"


def test_excessive_mutations_are_rate_limited(public_client: TestClient) -> None:
    headers = {"X-Demo-Session": "security-mutation-limit"}
    for _ in range(40):
        response = public_client.post(
            "/api/evidence/url",
            json={"url": "https://example.com/evidence.md"},
            headers=headers,
        )
        assert response.status_code == 403

    blocked = public_client.post(
        "/api/evidence/url",
        json={"url": "https://example.com/evidence.md"},
        headers=headers,
    )

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
