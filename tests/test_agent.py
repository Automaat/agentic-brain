from unittest.mock import MagicMock

import pytest

from src.agent import BrainAgent


@pytest.fixture
def mock_mcp_manager():
    return MagicMock()


@pytest.fixture
def agent(mock_mcp_manager):
    return BrainAgent("test-api-key", mock_mcp_manager)


def test_brain_agent_init(mock_mcp_manager):
    agent = BrainAgent("my-key", mock_mcp_manager)
    assert agent.api_key == "my-key"
    assert agent.mcp_manager == mock_mcp_manager


async def test_chat_basic(agent):
    response = await agent.chat(
        message="Hello",
        history=[],
        user_id="user-1",
        session_id="session-1",
        interface="api",
        language="en",
    )
    assert response == "Echo: Hello (history: 0 messages)"


async def test_chat_with_history(agent):
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
    assert response == "Echo: Second message (history: 2 messages)"


async def test_chat_counts_history_correctly(agent):
    history = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
    response = await agent.chat(
        message="Test",
        history=history,
        user_id="user-3",
        session_id="session-3",
        interface="api",
        language="en",
    )
    assert "history: 10 messages" in response
