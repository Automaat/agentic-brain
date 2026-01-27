from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def mock_state_manager():
    with patch("src.main.state_manager") as mock:
        mock.get_conversation = MagicMock(return_value=[])
        mock.add_message = MagicMock()
        mock.reset_session = MagicMock()
        yield mock


@pytest.fixture
def mock_agent():
    with patch("src.main.agent") as mock:
        mock.chat = AsyncMock(return_value="Test response")
        yield mock


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_endpoint_success(client, mock_state_manager, mock_agent):
    mock_state_manager.get_conversation.return_value = []
    mock_agent.chat.return_value = "Test response"

    response = client.post(
        "/chat",
        json={"message": "Hello", "interface": "api", "language": "en"},
        headers={"user-id": "user-123", "session-id": "session-456"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Test response"
    assert data["actions"] == []

    mock_state_manager.get_conversation.assert_called_once_with("session-456")
    assert mock_state_manager.add_message.call_count == 2
    mock_state_manager.add_message.assert_any_call("session-456", "user", "Hello")
    mock_state_manager.add_message.assert_any_call("session-456", "assistant", "Test response")


def test_chat_endpoint_with_defaults(client, mock_state_manager, mock_agent):
    response = client.post(
        "/chat",
        json={"message": "Hi"},
        headers={"user-id": "user-1", "session-id": "session-1"},
    )

    assert response.status_code == 200


def test_chat_endpoint_with_history(client, mock_state_manager, mock_agent):
    history = [{"role": "user", "content": "Previous message"}]
    mock_state_manager.get_conversation.return_value = history
    mock_agent.chat.return_value = "Response with context"

    response = client.post(
        "/chat",
        json={"message": "Follow-up"},
        headers={"user-id": "user-2", "session-id": "session-2"},
    )

    assert response.status_code == 200
    assert response.json()["response"] == "Response with context"


def test_chat_endpoint_missing_headers(client):
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 422


def test_chat_endpoint_missing_message(client):
    response = client.post(
        "/chat",
        json={},
        headers={"user-id": "user-1", "session-id": "session-1"},
    )
    assert response.status_code == 422


def test_chat_endpoint_exception_handling(client, mock_state_manager, mock_agent):
    mock_state_manager.get_conversation.return_value = []
    mock_agent.chat.side_effect = Exception("Test error")

    response = client.post(
        "/chat",
        json={"message": "Test"},
        headers={"user-id": "user-1", "session-id": "session-1"},
    )

    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]


def test_reset_session_endpoint(client, mock_state_manager):
    response = client.post(
        "/reset-session",
        headers={"session-id": "session-reset"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reset"
    assert data["session_id"] == "session-reset"
    mock_state_manager.reset_session.assert_called_once_with("session-reset")


def test_reset_session_missing_header(client):
    response = client.post("/reset-session")
    assert response.status_code == 422


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    # Prometheus CONTENT_TYPE_LATEST includes version info
    assert response.headers["content-type"] == "text/plain; version=1.0.0; charset=utf-8"
    assert b"http_requests_total" in response.content or b"# HELP" in response.content


def test_chat_custom_interface(client, mock_state_manager, mock_agent):
    response = client.post(
        "/chat",
        json={"message": "Test", "interface": "telegram", "language": "pl"},
        headers={"user-id": "user-1", "session-id": "session-1"},
    )

    assert response.status_code == 200
    mock_agent.chat.assert_called_once()
    call_kwargs = mock_agent.chat.call_args[1]
    assert call_kwargs["interface"] == "telegram"
    assert call_kwargs["language"] == "pl"


def test_chat_passes_all_parameters(client, mock_state_manager, mock_agent):
    history = [{"role": "user", "content": "Prev"}]
    mock_state_manager.get_conversation.return_value = history

    response = client.post(
        "/chat",
        json={"message": "New message", "interface": "voice", "language": "pl"},
        headers={"user-id": "user-abc", "session-id": "session-xyz"},
    )

    assert response.status_code == 200
    mock_agent.chat.assert_called_once_with(
        message="New message",
        history=history,
        user_id="user-abc",
        session_id="session-xyz",
        interface="voice",
        language="pl",
    )


async def test_lifespan_shutdown():
    from src.main import lifespan

    mock_app = MagicMock()

    with patch("src.main.mcp_manager") as mock_mcp:
        mock_mcp.connect_all = AsyncMock()
        mock_mcp.close = AsyncMock()

        async with lifespan(mock_app):
            mock_mcp.connect_all.assert_called_once()
            mock_mcp.close.assert_not_called()

        mock_mcp.close.assert_called_once()
