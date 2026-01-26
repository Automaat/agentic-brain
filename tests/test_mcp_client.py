from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.mcp_client import MCPManager


@pytest.fixture
def mock_servers():
    return {
        "filesystem": "http://localhost:8001/sse",
        "shell": "http://localhost:8002/sse",
    }


@pytest.fixture
def mcp_manager(mock_servers):
    return MCPManager(mock_servers)


def test_mcp_manager_init(mock_servers):
    manager = MCPManager(mock_servers)
    assert manager.servers == mock_servers
    assert manager.tools == {}
    assert isinstance(manager.client, httpx.AsyncClient)


async def test_connect_all_success(mcp_manager):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"tools": [{"name": "test_tool"}]}

    with patch.object(mcp_manager.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await mcp_manager.connect_all()

        assert "filesystem" in mcp_manager.tools
        assert "shell" in mcp_manager.tools
        assert mcp_manager.tools["filesystem"] == [{"name": "test_tool"}]


async def test_connect_all_with_failures(mcp_manager, caplog):
    import logging

    call_count = 0

    async def mock_discover(name, url):
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # First call fails
            raise Exception("Connection timeout")
        # Second call succeeds
        mcp_manager.tools[name] = [{"name": "shell_tool"}]

    with patch.object(mcp_manager, "_discover_tools", new_callable=AsyncMock) as mock_discover_obj:
        mock_discover_obj.side_effect = mock_discover

        with caplog.at_level(logging.WARNING, logger="src.mcp_client"):
            await mcp_manager.connect_all()

        assert "shell" in mcp_manager.tools
        assert mcp_manager.tools["shell"] == [{"name": "shell_tool"}]
        # Verify warning was logged for failed connection
        assert any("Failed to connect" in record.getMessage() for record in caplog.records)


async def test_discover_tools_success(mcp_manager):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"tools": [{"name": "read_file"}, {"name": "write_file"}]}

    with patch.object(mcp_manager.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await mcp_manager._discover_tools("filesystem", "http://localhost:8001/sse")

        assert mcp_manager.tools["filesystem"] == [
            {"name": "read_file"},
            {"name": "write_file"},
        ]


async def test_discover_tools_empty_response(mcp_manager):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}

    with patch.object(mcp_manager.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await mcp_manager._discover_tools("filesystem", "http://localhost:8001/sse")

        assert mcp_manager.tools["filesystem"] == []


async def test_discover_tools_failure(mcp_manager):
    with patch.object(mcp_manager.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection failed")
        await mcp_manager._discover_tools("filesystem", "http://localhost:8001/sse")

        assert mcp_manager.tools["filesystem"] == []


async def test_discover_tools_non_200_status(mcp_manager):
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch.object(mcp_manager.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await mcp_manager._discover_tools("filesystem", "http://localhost:8001/sse")

        assert "filesystem" not in mcp_manager.tools


async def test_call_tool_success(mcp_manager):
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": "success"}

    with patch.object(mcp_manager.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await mcp_manager.call_tool("filesystem", "read_file", {"path": "/test"})

        assert result == {"result": "success"}
        mock_post.assert_called_once_with(
            "http://localhost:8001/call",
            json={"tool": "read_file", "arguments": {"path": "/test"}},
        )


async def test_call_tool_unknown_server(mcp_manager):
    with pytest.raises(ValueError, match="Unknown MCP server: unknown"):
        await mcp_manager.call_tool("unknown", "test_tool", {})


async def test_call_tool_http_error(mcp_manager):
    with patch.object(mcp_manager.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPError("Request failed")

        with pytest.raises(httpx.HTTPError):
            await mcp_manager.call_tool("filesystem", "read_file", {})


async def test_call_tool_raises_for_status(mcp_manager):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Error", request=MagicMock(), response=MagicMock()
    )

    with patch.object(mcp_manager.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            await mcp_manager.call_tool("filesystem", "test_tool", {})


async def test_get_available_tools_empty(mcp_manager):
    tools = await mcp_manager.get_available_tools()
    assert tools == []


async def test_get_available_tools_with_tools(mcp_manager):
    mcp_manager.tools = {
        "filesystem": [{"name": "read_file", "description": "Read a file"}],
        "shell": [{"name": "exec", "description": "Execute command"}],
    }

    tools = await mcp_manager.get_available_tools()

    assert len(tools) == 2
    assert tools[0]["name"] == "read_file"
    assert tools[0]["server"] == "filesystem"
    assert tools[1]["name"] == "exec"
    assert tools[1]["server"] == "shell"


async def test_get_available_tools_preserves_original(mcp_manager):
    original_tool = {"name": "test_tool", "description": "Test"}
    mcp_manager.tools = {"test": [original_tool]}

    tools = await mcp_manager.get_available_tools()

    # Verify original wasn't modified
    assert "server" not in original_tool
    # Verify returned copy has server
    assert tools[0]["server"] == "test"


async def test_close(mcp_manager):
    with patch.object(mcp_manager.client, "aclose", new_callable=AsyncMock) as mock_close:
        await mcp_manager.close()
        mock_close.assert_called_once()


async def test_multiple_tools_same_server(mcp_manager):
    mcp_manager.tools = {
        "filesystem": [
            {"name": "read", "desc": "Read"},
            {"name": "write", "desc": "Write"},
            {"name": "delete", "desc": "Delete"},
        ]
    }

    tools = await mcp_manager.get_available_tools()

    assert len(tools) == 3
    assert all(t["server"] == "filesystem" for t in tools)


async def test_get_available_tools_cache_hit(mcp_manager):
    mcp_manager.tools = {"server1": [{"name": "tool1"}]}

    # First call - cache miss
    tools1 = await mcp_manager.get_available_tools()
    assert len(tools1) == 1
    assert mcp_manager._tools_cache is not None

    # Modify tools dict
    mcp_manager.tools = {"server1": [{"name": "tool1"}, {"name": "tool2"}]}

    # Second call - cache hit (should return cached value, not updated tools)
    tools2 = await mcp_manager.get_available_tools()
    assert len(tools2) == 1  # Still returns cached value
    assert tools2 == tools1


async def test_cache_invalidation_on_connect(mcp_manager):
    mcp_manager.tools = {"server1": [{"name": "tool1"}]}

    # First call - populate cache
    tools1 = await mcp_manager.get_available_tools()
    assert len(tools1) == 1
    assert mcp_manager._tools_cache is not None

    # Call connect_all which should invalidate cache
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"tools": [{"name": "tool1"}, {"name": "tool2"}]}

    with patch.object(mcp_manager.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await mcp_manager.connect_all()

    # Cache should be invalidated
    assert mcp_manager._tools_cache is None


def test_get_endpoint(mcp_manager):
    url = "http://localhost:8001/sse"
    result = mcp_manager._get_endpoint(url, "tools")
    assert result == "http://localhost:8001/tools"

    url2 = "https://example.com:8080/sse"
    result2 = mcp_manager._get_endpoint(url2, "call")
    assert result2 == "https://example.com:8080/call"
