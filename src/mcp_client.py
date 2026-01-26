import logging
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

logger = logging.getLogger(__name__)


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
        for name, url in self.servers.items():
            try:
                await self._discover_tools(name, url)
                logger.info(f"Connected to MCP server: {name} at {url}")
            except Exception as e:
                logger.warning(f"Failed to connect to {name} at {url}: {e}")

    def _get_endpoint(self, url: str, endpoint: str) -> str:
        """Convert SSE URL to endpoint URL"""
        parsed = urlparse(url)
        new_path = parsed.path.replace('/sse', f'/{endpoint}')
        return urlunparse(parsed._replace(path=new_path))

    async def _discover_tools(self, server_name: str, url: str) -> None:
        """Discover available tools from an MCP server"""
        try:
            # MCP servers expose tools via /tools endpoint
            response = await self.client.get(self._get_endpoint(url, 'tools'))
            if response.status_code == 200:
                tools_data = response.json()
                self.tools[server_name] = tools_data.get("tools", [])
        except Exception as e:
            logger.debug(f"Could not discover tools for {server_name}: {e}")
            # Initialize empty tools list for this server
            self.tools[server_name] = []

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on a specific MCP server"""
        if server_name not in self.servers:
            raise ValueError(f"Unknown MCP server: {server_name}")

        url = self._get_endpoint(self.servers[server_name], 'call')
        payload = {"tool": tool_name, "arguments": arguments}

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on {server_name}: {e}")
            raise

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
