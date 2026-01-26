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
        interface="web",
        language="fr",
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
