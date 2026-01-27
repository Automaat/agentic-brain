from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert data["version"] == "1.0.0"
    assert "components" in data
    assert "redis" in data["components"]
    assert "mcp_servers" in data["components"]
