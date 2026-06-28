from fastapi.testclient import TestClient

from recallops.main import create_app


def test_health_is_safe_and_reports_fake_mode() -> None:
    response = TestClient(create_app()).get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["memory"]["mode"] == "fake"
    assert body["demo_mode"] is True
    assert "api_key" not in response.text.lower()
    assert "secret" not in response.text.lower()
