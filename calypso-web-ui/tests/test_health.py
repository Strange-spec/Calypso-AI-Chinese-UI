from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_system_status():
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == settings.app_name
    assert data["version"] == settings.version
    assert data["mode"] == settings.app_mode
    assert data["base_url"] == settings.calypso_base_url
    assert "has_token" in data
    assert isinstance(data["has_token"], bool)
