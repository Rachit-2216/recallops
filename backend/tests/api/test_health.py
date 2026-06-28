from fastapi.testclient import TestClient

from recallops.main import create_app
from recallops.memory.fake import FakeCogneeAdapter


def test_health_is_safe_and_reports_fake_mode() -> None:
    response = TestClient(create_app()).get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["memory"]["mode"] == "fake"
    assert body["demo_mode"] is True
    assert "api_key" not in response.text.lower()
    assert "secret" not in response.text.lower()


def test_health_reports_degraded_memory_without_provider_details() -> None:
    memory = FakeCogneeAdapter(fail_operations={"health"})
    response = TestClient(create_app(memory=memory)).get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["memory"]["reachable"] is False
    assert response.json()["memory"]["dataset_ready"] is False
    assert "configured fake" not in response.text.casefold()
