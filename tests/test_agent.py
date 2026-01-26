from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from src.agent import BrainAgent


@pytest.fixture
def mock_mcp_manager():
    return MagicMock()


@pytest.fixture
def agent(mock_mcp_manager):
    with patch("src.agent.ChatAnthropic"):
        agent_instance = BrainAgent("test-api-key", mock_mcp_manager)
        agent_instance.model = AsyncMock()
        return agent_instance


def test_brain_agent_init(mock_mcp_manager):
    with patch("src.agent.ChatAnthropic"):
        agent = BrainAgent("my-key", mock_mcp_manager)
        assert agent.api_key == "my-key"
        assert agent.mcp_manager == mock_mcp_manager


async def test_chat_basic(agent):
    # Mock the graph to return a simple response
    agent.model.ainvoke = AsyncMock(return_value=AIMessage(content="Hello! How can I help you?"))

    response = await agent.chat(
        message="Hello",
        history=[],
        user_id="user-1",
        session_id="session-1",
        interface="api",
        language="en",
    )

    assert isinstance(response, str)
    assert len(response) > 0


async def test_chat_with_history(agent):
    agent.model.ainvoke = AsyncMock(
        return_value=AIMessage(content="I see you mentioned something earlier. How can I help?")
    )

    history = [
        {"role": "user", "content": "First message"},
        {"role": "assistant", "content": "First response"},
    ]

    response = await agent.chat(
        message="Second message",
        history=history,
        user_id="user-2",
        session_id="session-2",
        interface="telegram",
        language="en",
    )

    assert isinstance(response, str)
    assert len(response) > 0


async def test_chat_counts_history_correctly(agent):
    agent.model.ainvoke = AsyncMock(return_value=AIMessage(content="Got it!"))

    history = [{"role": "user", "content": f"Message {i}"} for i in range(10)]

    response = await agent.chat(
        message="Test",
        history=history,
        user_id="user-3",
        session_id="session-3",
        interface="api",
        language="en",
    )

    assert isinstance(response, str)
    assert len(response) > 0


async def test_convert_history_to_messages(agent):
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "system", "content": "System message"},
    ]

    messages = agent._convert_history_to_messages(history)
    assert len(messages) == 3
    assert messages[0].content == "Hello"
    assert messages[1].content == "Hi there!"
    assert messages[2].content == "System message"


def test_build_system_prompt(agent):
    prompt = agent._build_system_prompt("voice", "pl")
    assert "voice" in prompt.lower() or "concise" in prompt.lower()
    assert "Polish" in prompt or "pl" in prompt.lower()

    prompt_api = agent._build_system_prompt("api", "en")
    assert len(prompt_api) > 0


async def test_chat_error_handling(agent):
    # Make the graph raise an exception
    agent.graph.ainvoke = AsyncMock(side_effect=Exception("Test error"))

    response = await agent.chat(
        message="Test",
        history=[],
        user_id="user-1",
        session_id="session-1",
        interface="api",
        language="en",
    )

    assert response == "I apologize, I couldn't generate a response. Please try again."


async def test_chat_empty_response(agent):
    # Mock graph to return empty messages
    agent.graph.ainvoke = AsyncMock(return_value={"messages": []})

    response = await agent.chat(
        message="Test",
        history=[],
        user_id="user-1",
        session_id="session-1",
        interface="api",
        language="en",
    )

    assert response == "I apologize, I couldn't generate a response."


async def test_chat_empty_content(agent):
    # Mock graph to return message with empty content
    agent.graph.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content="")]})

    response = await agent.chat(
        message="Test",
        history=[],
        user_id="user-1",
        session_id="session-1",
        interface="api",
        language="en",
    )

    assert response == "I apologize, I couldn't generate a response."


def test_should_continue_with_tool_calls(agent):
    from langchain_core.messages import ToolCall

    # Create message with tool calls
    message_with_tools = AIMessage(
        content="Using tools",
        tool_calls=[ToolCall(name="test_tool", args={}, id="123", type="tool_call")],
    )

    result = agent._should_continue({"messages": [message_with_tools]})
    assert result == "continue"


def test_should_continue_without_tool_calls(agent):
    message_without_tools = AIMessage(content="No tools needed")

    result = agent._should_continue({"messages": [message_without_tools]})
    assert result == "end"


def test_convert_mcp_tools_to_langchain(agent):
    mcp_tools = [
        {
            "name": "read_file",
            "description": "Read a file",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
            "server": "filesystem",
        },
        {
            "name": "list_dir",
            "description": "List directory",
            "inputSchema": {"type": "object", "properties": {}},
            "server": "filesystem",
        },
    ]

    lc_tools = agent._convert_mcp_tools_to_langchain(mcp_tools)

    assert len(lc_tools) == 2
    assert lc_tools[0]["type"] == "function"
    assert lc_tools[0]["function"]["name"] == "read_file"
    assert lc_tools[0]["function"]["description"] == "Read a file"
    assert "path" in lc_tools[0]["function"]["parameters"]["properties"]
    assert lc_tools[1]["function"]["name"] == "list_dir"


def test_convert_mcp_tools_without_description(agent):
    mcp_tools = [{"name": "tool1", "server": "server1"}]
    lc_tools = agent._convert_mcp_tools_to_langchain(mcp_tools)

    assert lc_tools[0]["function"]["description"] == ""
    assert lc_tools[0]["function"]["parameters"] == {"type": "object", "properties": {}}


async def test_call_model_with_tools(agent):
    from langchain_core.messages import HumanMessage

    agent.mcp_manager.get_available_tools = AsyncMock(
        return_value=[
            {
                "name": "test_tool",
                "description": "A test tool",
                "inputSchema": {"type": "object", "properties": {}},
                "server": "test",
            }
        ]
    )

    mock_response = AIMessage(content="Response")
    agent.model.bind_tools = MagicMock(return_value=agent.model)
    agent.model.ainvoke = AsyncMock(return_value=mock_response)

    state = {"messages": [HumanMessage(content="Test")]}
    result = await agent._call_model(state)

    assert result["messages"][0] == mock_response
    agent.model.bind_tools.assert_called_once()


async def test_call_model_without_tools(agent):
    from langchain_core.messages import HumanMessage

    agent.mcp_manager.get_available_tools = AsyncMock(return_value=[])

    mock_response = AIMessage(content="Response")
    agent.model.ainvoke = AsyncMock(return_value=mock_response)

    state = {"messages": [HumanMessage(content="Test")]}
    result = await agent._call_model(state)

    assert result["messages"][0] == mock_response


async def test_execute_tools_success(agent):
    from langchain_core.messages import ToolCall, ToolMessage

    tool_call = ToolCall(name="read_file", args={"path": "/test"}, id="call_123", type="tool_call")
    message_with_tool = AIMessage(content="", tool_calls=[tool_call])

    agent.mcp_manager.get_available_tools = AsyncMock(
        return_value=[{"name": "read_file", "server": "filesystem"}]
    )
    agent.mcp_manager.call_tool = AsyncMock(return_value={"content": "file content"})

    state = {"messages": [message_with_tool]}
    result = await agent._execute_tools(state)

    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], ToolMessage)
    assert "file content" in result["messages"][0].content
    agent.mcp_manager.call_tool.assert_called_once_with("filesystem", "read_file", {"path": "/test"})


async def test_execute_tools_not_found(agent):
    from langchain_core.messages import ToolCall, ToolMessage

    tool_call = ToolCall(name="unknown_tool", args={}, id="call_456", type="tool_call")
    message_with_tool = AIMessage(content="", tool_calls=[tool_call])

    agent.mcp_manager.get_available_tools = AsyncMock(return_value=[{"name": "other_tool", "server": "test"}])

    state = {"messages": [message_with_tool]}
    result = await agent._execute_tools(state)

    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], ToolMessage)
    assert "Error: Tool unknown_tool not found" in result["messages"][0].content


async def test_execute_tools_exception(agent):
    from langchain_core.messages import ToolCall, ToolMessage

    tool_call = ToolCall(name="failing_tool", args={}, id="call_789", type="tool_call")
    message_with_tool = AIMessage(content="", tool_calls=[tool_call])

    agent.mcp_manager.get_available_tools = AsyncMock(
        return_value=[{"name": "failing_tool", "server": "test"}]
    )
    agent.mcp_manager.call_tool = AsyncMock(side_effect=Exception("Tool execution failed"))

    state = {"messages": [message_with_tool]}
    result = await agent._execute_tools(state)

    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], ToolMessage)
    assert "Error: Tool execution failed" in result["messages"][0].content


async def test_execute_tools_no_tool_calls(agent):
    message = AIMessage(content="No tools")

    state = {"messages": [message]}
    result = await agent._execute_tools(state)

    assert result["messages"] == []


def test_convert_history_with_unknown_role(agent):
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "unknown_role", "content": "Should be skipped"},
        {"role": "assistant", "content": "Hi"},
    ]

    with patch("src.agent.logger") as mock_logger:
        messages = agent._convert_history_to_messages(history)
        assert len(messages) == 2
        assert messages[0].content == "Hello"
        assert messages[1].content == "Hi"
        mock_logger.warning.assert_called_once()
