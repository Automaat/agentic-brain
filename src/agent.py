from typing import Any

from .mcp_client import MCPManager


class BrainAgent:
    """LangGraph agentic loop - TODO: implement"""

    def __init__(self, api_key: str, mcp_manager: MCPManager):
        self.api_key = api_key
        self.mcp_manager = mcp_manager

    async def chat(
        self,
        message: str,
        history: list[dict[str, Any]],
        user_id: str,
        session_id: str,
        interface: str,
        language: str,
    ) -> str:
        # TODO: Implement LangGraph agentic loop with history
        # For now, return simple echo with history count
        return f"Echo: {message} (history: {len(history)} messages)"
