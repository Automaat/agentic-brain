import logging
from typing import Annotated, Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from .config import settings
from .mcp_client import MCPManager

logger = logging.getLogger(__name__)


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
        self.model = ChatAnthropic(
            api_key=api_key,
            model_name=settings.default_model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._call_model)  # type: ignore[no-matching-overload]
        workflow.add_node("tools", ToolNode([]))  # MCP tools will be added dynamically

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

    async def _call_model(self, state: AgentState) -> dict[str, Any]:
        """Call the Claude model"""
        messages = state["messages"]
        response = await self.model.ainvoke(messages)
        return {"messages": [response]}

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

        return messages

    async def chat(
        self,
        message: str,
        history: list[dict[str, Any]],
        user_id: str,
        session_id: str,
        interface: str,
        language: str,
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
                if isinstance(last_message, AIMessage):
                    content = last_message.content
                    return str(content) if content else "I apologize, I couldn't generate a response."
                return (
                    str(last_message.content)
                    if last_message.content
                    else "I apologize, I couldn't generate a response."
                )

            return "I apologize, I couldn't generate a response."

        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            return f"An error occurred: {e!s}"
