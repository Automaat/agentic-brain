import time
from typing import Any
from urllib.parse import urlparse

import httpx

from .logging_config import get_logger
from .metrics import mcp_servers_connected, mcp_tool_calls_total, mcp_tool_duration_seconds
from .retry import retry_on_network_error

logger = get_logger(__name__)


class MCPManager:
    """MCP client manager for connecting to MCP servers via SSE"""

    def __init__(self, servers: dict[str, str]):
        self.servers = servers
        self.tools: dict[str, Any] = {}
        self.client = httpx.AsyncClient(timeout=30.0)
        self._tools_cache: list[dict[str, Any]] | None = None

    async def connect_all(self) -> None:
        """Connect to all configured MCP servers and discover tools"""
        self._tools_cache = None  # Invalidate cache
        logger.info("Connecting to MCP servers", server_count=len(self.servers))

        connected = 0
        for name, url in self.servers.items():
            try:
                await self._discover_tools(name, url)
                tool_count = len(self.tools.get(name, []))
                logger.info("Connected to MCP server", server=name, url=url, tool_count=tool_count)
                connected += 1
            except Exception as e:
                logger.warning("Failed to connect to MCP server", server=name, url=url, error=str(e))

        mcp_servers_connected.set(connected)

    def _get_endpoint(self, url: str, endpoint: str) -> str:
        """Convert SSE URL to endpoint URL"""
        parsed = urlparse(url)
        new_path = parsed.path.replace("/sse", f"/{endpoint}")
        # Build new URL from components
        return f"{parsed.scheme}://{parsed.netloc}{new_path}"

    @retry_on_network_error(max_attempts=3)
    async def _discover_tools(self, server_name: str, url: str) -> None:
        """Discover available tools from an MCP server"""
        try:
            # MCP servers expose tools via /tools endpoint
            tools_url = self._get_endpoint(url, "tools")
            logger.debug("Discovering tools", server=server_name, url=tools_url)
            response = await self.client.get(tools_url)
            if response.status_code == 200:
                tools_data = response.json()
                self.tools[server_name] = tools_data.get("tools", [])
                logger.debug("Tools discovered", server=server_name, tool_count=len(self.tools[server_name]))
        except Exception as e:
            logger.debug("Could not discover tools", server=server_name, error=str(e))
            # Initialize empty tools list for this server
            self.tools[server_name] = []

    @retry_on_network_error(max_attempts=3)
    async def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on a specific MCP server"""
        if server_name not in self.servers:
            raise ValueError(f"Unknown MCP server: {server_name}")

        url = self._get_endpoint(self.servers[server_name], "call")
        payload = {"tool": tool_name, "arguments": arguments}

        logger.debug("Calling MCP tool", server=server_name, tool=tool_name, url=url)

        start_time = time.time()
        status = "error"

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            status = "success"
            logger.debug("MCP tool call succeeded", server=server_name, tool=tool_name)
            return result
        except Exception as e:
            logger.error(
                "MCP tool call failed",
                server=server_name,
                tool=tool_name,
                error=str(e),
                exc_info=True,
            )
            raise
        finally:
            duration = time.time() - start_time
            mcp_tool_calls_total.labels(server=server_name, tool=tool_name, status=status).inc()
            mcp_tool_duration_seconds.labels(server=server_name, tool=tool_name).observe(duration)

    async def get_available_tools(self) -> list[dict[str, Any]]:
        """Get all available tools across all connected servers"""
        if self._tools_cache is not None:
            return self._tools_cache

        all_tools = []
        for server_name, tools in self.tools.items():
            for tool in tools:
                tool_copy = tool.copy()
                tool_copy["server"] = server_name
                all_tools.append(tool_copy)

        self._tools_cache = all_tools
        return all_tools

    async def close(self) -> None:
        """Close all connections"""
        await self.client.aclose()
