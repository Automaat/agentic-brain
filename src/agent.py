from typing import Annotated, Any, Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from .config import settings
from .logging_config import get_logger
from .mcp_client import MCPManager

logger = get_logger(__name__)


class AgentState(TypedDict):
    """State for the agent graph"""

    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str
    interface: str
    language: str


class BrainAgent:
    """LangGraph agentic loop with Claude Sonnet 4.5"""

    def __init__(self, api_key: str, mcp_manager: MCPManager):
        self.api_key = api_key
        self.mcp_manager = mcp_manager
        self.model = self._create_llm_model()
        self.graph = self._build_graph()

    def _create_llm_model(self):
        """Create LLM model based on configured provider"""
        if settings.llm_provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=settings.temperature,
            )
        else:
            return ChatAnthropic(
                api_key=self.api_key,
                model_name=settings.default_model,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
            )

    def _build_graph(self) -> Any:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._call_model)  # type: ignore[no-matching-overload]
        workflow.add_node("tools", self._execute_tools)  # type: ignore[no-matching-overload]

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges for tool calling
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END,
            },
        )

        # After tools, go back to agent
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def _convert_mcp_tools_to_langchain(self, mcp_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert MCP tool format to LangChain tool schema"""
        lc_tools = []
        for tool in mcp_tools:
            # MCP format: {name, description, inputSchema, server}
            # LangChain needs: dict with type="function" and function schema
            lc_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
                },
            }
            lc_tools.append(lc_tool)
        return lc_tools

    async def _call_model(self, state: AgentState) -> dict[str, Any]:
        """Call Claude with dynamically bound MCP tools"""
        messages = state["messages"]

        # Get MCP tools and bind to model
        mcp_tools = await self.mcp_manager.get_available_tools()
        logger.debug(
            "Calling model",
            tool_count=len(mcp_tools),
            session_id=state.get("session_id"),
        )

        if mcp_tools:
            lc_tools = self._convert_mcp_tools_to_langchain(mcp_tools)
            model_with_tools = self.model.bind_tools(lc_tools)
            response = await model_with_tools.ainvoke(messages)
        else:
            response = await self.model.ainvoke(messages)

        return {"messages": [response]}

    async def _execute_tools(self, state: AgentState) -> dict[str, Any]:
        """Execute MCP tool calls"""
        messages = state["messages"]
        last_message = messages[-1]

        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"messages": []}

        # Execute each tool call via MCP
        results = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            args = tool_call.get("args", {})

            # Find which server owns this tool
            mcp_tools = await self.mcp_manager.get_available_tools()
            server_name = next((t["server"] for t in mcp_tools if t["name"] == tool_name), None)

            if not server_name:
                results.append(ToolMessage(content=f"Error: Tool {tool_name} not found", tool_call_id=tool_call["id"]))
                continue

            try:
                logger.info("Executing tool", tool_name=tool_name, server=server_name)
                result = await self.mcp_manager.call_tool(server_name, tool_name, args)
                results.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
                logger.info("Tool execution succeeded", tool_name=tool_name)
            except Exception as e:
                logger.error("Tool execution failed", tool_name=tool_name, error=str(e), exc_info=True)
                results.append(ToolMessage(content=f"Error: {e!s}", tool_call_id=tool_call["id"]))

        return {"messages": results}

    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue to tools or end"""
        messages = state["messages"]
        last_message = messages[-1]

        # If the last message has tool calls, continue to tools
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "continue"

        return "end"

    def _build_system_prompt(self, interface: str, language: str) -> str:
        """Build system prompt based on interface and language"""
        base_prompt = """You are a helpful AI assistant with access to various tools and systems.
You can help with tasks, answer questions, and interact with connected services."""

        interface_prompts = {
            "voice": "The user is interacting via voice. Keep responses concise and conversational.",
            "telegram": "The user is messaging via Telegram. Use clear, formatted text.",
            "api": "This is a programmatic API interaction.",
        }

        language_prompts = {
            "pl": "Respond in Polish.",
            "en": "Respond in English.",
        }

        parts = [base_prompt]
        if interface in interface_prompts:
            parts.append(interface_prompts[interface])
        if language in language_prompts:
            parts.append(language_prompts[language])

        return "\n\n".join(parts)

    def _convert_history_to_messages(self, history: list[dict[str, Any]]) -> list[BaseMessage]:
        """Convert Redis history format to LangChain messages"""
        messages: list[BaseMessage] = []
        for msg in history:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))
            else:
                logger.warning("Unrecognized role '%s', skipping: %r", role, msg)

        return messages

    async def chat(
        self,
        message: str,
        history: list[dict[str, Any]],
        user_id: str,
        session_id: str,
        interface: Literal["voice", "telegram", "api"],
        language: Literal["pl", "en"],
    ) -> str:
        """Process a chat message through the agentic loop"""
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt(interface, language)

            # Convert history to messages
            messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
            messages.extend(self._convert_history_to_messages(history))
            messages.append(HumanMessage(content=message))

            # Create initial state
            initial_state: AgentState = {
                "messages": messages,
                "user_id": user_id,
                "session_id": session_id,
                "interface": interface,
                "language": language,
            }

            # Run the graph
            result = await self.graph.ainvoke(initial_state)

            # Extract the final response
            final_messages = result["messages"]
            if final_messages:
                last_message = final_messages[-1]
                content = getattr(last_message, "content", None)
                return str(content) if content else "I apologize, I couldn't generate a response."

            return "I apologize, I couldn't generate a response."

        except Exception as e:
            logger.error("Chat processing failed", session_id=session_id, error=str(e), exc_info=True)
            return "I apologize, I couldn't generate a response. Please try again."
