from pathlib import Path

from fastapi.testclient import TestClient

from recallops.main import create_app

SPA_FIXTURE = Path(__file__).parents[1] / "fixtures" / "spa-dist"


def test_built_frontend_is_served_with_spa_fallback() -> None:
    client = TestClient(create_app(frontend_dist=SPA_FIXTURE))

    app_route = client.get("/app/incidents/INC-2048")
    asset = client.get("/assets/app.js")
    missing_api = client.get("/api/route-that-does-not-exist")

    assert app_route.status_code == 200
    assert "RecallOps SPA" in app_route.text
    assert asset.status_code == 200
    assert missing_api.status_code == 404
    assert missing_api.json()["error"]["code"] == "NOT_FOUND"
