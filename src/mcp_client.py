import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MCPManager:
    """MCP client manager for connecting to MCP servers via SSE"""

    def __init__(self, servers: dict[str, str]):
        self.servers = servers
        self.tools: dict[str, Any] = {}
        self.client = httpx.AsyncClient(timeout=30.0)

    async def connect_all(self) -> None:
        """Connect to all configured MCP servers and discover tools"""
        for name, url in self.servers.items():
            try:
                await self._discover_tools(name, url)
                logger.info(f"Connected to MCP server: {name} at {url}")
            except Exception as e:
                logger.warning(f"Failed to connect to {name} at {url}: {e}")

    async def _discover_tools(self, server_name: str, url: str) -> None:
        """Discover available tools from an MCP server"""
        try:
            # MCP servers expose tools via /tools endpoint
            response = await self.client.get(f"{url.replace('/sse', '/tools')}")
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

        url = self.servers[server_name].replace("/sse", "/call")
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
        all_tools = []
        for server_name, tools in self.tools.items():
            for tool in tools:
                tool_copy = tool.copy()
                tool_copy["server"] = server_name
                all_tools.append(tool_copy)
        return all_tools

    async def close(self) -> None:
        """Close all connections"""
        await self.client.aclose()
