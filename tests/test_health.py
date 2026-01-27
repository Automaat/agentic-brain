from unittest.mock import MagicMock

import pytest
import redis
from fastapi.testclient import TestClient

from src.health import check_health
from src.main import app
from src.mcp_client import MCPManager
from src.state import StateManager

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


@pytest.mark.anyio
async def test_check_health_all_healthy() -> None:
    """Test health check when all components are healthy."""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    state_manager = MagicMock(spec=StateManager)
    state_manager.redis = redis_mock

    mcp_manager = MagicMock(spec=MCPManager)
    mcp_manager.servers = {"server1": MagicMock(), "server2": MagicMock()}
    mcp_manager.tools = {"server1": ["tool1", "tool2"], "server2": ["tool3"]}

    result = await check_health(state_manager, mcp_manager)

    assert result["status"] == "healthy"
    assert result["version"] == "1.0.0"
    assert result["components"]["redis"]["status"] == "healthy"
    assert result["components"]["mcp_servers"]["status"] == "healthy"
    assert result["components"]["mcp_servers"]["healthy"] == 2
    assert result["components"]["mcp_servers"]["total"] == 2


@pytest.mark.anyio
async def test_check_health_redis_connection_error() -> None:
    """Test health check when Redis has connection error."""
    redis_mock = MagicMock()
    redis_mock.ping.side_effect = redis.ConnectionError("Connection failed")
    state_manager = MagicMock(spec=StateManager)
    state_manager.redis = redis_mock

    mcp_manager = MagicMock(spec=MCPManager)
    mcp_manager.servers = {"server1": MagicMock()}
    mcp_manager.tools = {"server1": ["tool1"]}

    result = await check_health(state_manager, mcp_manager)

    assert result["status"] == "unhealthy"
    assert result["components"]["redis"]["status"] == "unhealthy"
    assert "error" in result["components"]["redis"]


@pytest.mark.anyio
async def test_check_health_redis_timeout() -> None:
    """Test health check when Redis times out."""
    redis_mock = MagicMock()
    redis_mock.ping.side_effect = redis.TimeoutError("Timeout")
    state_manager = MagicMock(spec=StateManager)
    state_manager.redis = redis_mock

    mcp_manager = MagicMock(spec=MCPManager)
    mcp_manager.servers = {"server1": MagicMock()}
    mcp_manager.tools = {"server1": ["tool1"]}

    result = await check_health(state_manager, mcp_manager)

    assert result["status"] == "unhealthy"
    assert result["components"]["redis"]["status"] == "unhealthy"


@pytest.mark.anyio
async def test_check_health_no_mcp_servers() -> None:
    """Test health check when no MCP servers are connected."""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    state_manager = MagicMock(spec=StateManager)
    state_manager.redis = redis_mock

    mcp_manager = MagicMock(spec=MCPManager)
    mcp_manager.servers = {}
    mcp_manager.tools = {}

    result = await check_health(state_manager, mcp_manager)

    # Zero configured servers treated as healthy (optional component)
    assert result["status"] == "healthy"
    assert result["components"]["redis"]["status"] == "healthy"
    assert result["components"]["mcp_servers"]["status"] == "healthy"
    assert result["components"]["mcp_servers"]["healthy"] == 0
    assert result["components"]["mcp_servers"]["total"] == 0


@pytest.mark.anyio
async def test_check_health_mcp_server_no_tools() -> None:
    """Test health check when MCP server has no tools."""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    state_manager = MagicMock(spec=StateManager)
    state_manager.redis = redis_mock

    mcp_manager = MagicMock(spec=MCPManager)
    mcp_manager.servers = {"server1": MagicMock(), "server2": MagicMock()}
    mcp_manager.tools = {"server1": ["tool1"], "server2": []}

    result = await check_health(state_manager, mcp_manager)

    # Partial failure = degraded component and overall status
    assert result["status"] == "degraded"
    assert result["components"]["mcp_servers"]["status"] == "degraded"
    assert result["components"]["mcp_servers"]["healthy"] == 1
    assert result["components"]["mcp_servers"]["total"] == 2
    assert result["components"]["mcp_servers"]["servers"]["server1"]["status"] == "healthy"
    assert result["components"]["mcp_servers"]["servers"]["server2"]["status"] == "unhealthy"


@pytest.mark.anyio
async def test_check_health_all_mcp_servers_unhealthy() -> None:
    """Test health check when all MCP servers are unhealthy."""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    state_manager = MagicMock(spec=StateManager)
    state_manager.redis = redis_mock

    mcp_manager = MagicMock(spec=MCPManager)
    mcp_manager.servers = {"server1": MagicMock()}
    mcp_manager.tools = {"server1": []}

    result = await check_health(state_manager, mcp_manager)

    # All servers unhealthy = unhealthy component, degraded overall
    assert result["status"] == "degraded"
    assert result["components"]["mcp_servers"]["status"] == "unhealthy"
    assert result["components"]["mcp_servers"]["healthy"] == 0


@pytest.mark.anyio
async def test_check_health_partial_mcp_servers() -> None:
    """Test health check when some MCP servers are unhealthy."""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    state_manager = MagicMock(spec=StateManager)
    state_manager.redis = redis_mock

    mcp_manager = MagicMock(spec=MCPManager)
    mcp_manager.servers = {"server1": MagicMock(), "server2": MagicMock(), "server3": MagicMock()}
    mcp_manager.tools = {"server1": ["tool1"], "server2": [], "server3": ["tool2"]}

    result = await check_health(state_manager, mcp_manager)

    assert result["status"] == "degraded"
    assert result["components"]["mcp_servers"]["healthy"] == 2
    assert result["components"]["mcp_servers"]["total"] == 3
