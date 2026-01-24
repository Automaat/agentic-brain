import json
from unittest.mock import MagicMock, patch

import pytest

from src.state import StateManager


@pytest.fixture
def mock_redis():
    with patch("src.state.redis.Redis") as mock:
        redis_instance = MagicMock()
        mock.return_value = redis_instance
        yield redis_instance


def test_state_manager_init():
    with patch("src.state.redis.Redis") as mock_redis_class:
        StateManager("localhost", 6379, 0)
        mock_redis_class.assert_called_once_with(host="localhost", port=6379, db=0, decode_responses=True)


def test_get_conversation_empty(mock_redis):
    mock_redis.lrange.return_value = []
    manager = StateManager("localhost", 6379, 0)
    messages = manager.get_conversation("session-123")
    assert messages == []
    mock_redis.lrange.assert_called_once_with("session:session-123:messages", 0, -1)


def test_get_conversation_with_messages(mock_redis):
    mock_messages = [
        json.dumps({"role": "user", "content": "Hello"}),
        json.dumps({"role": "assistant", "content": "Hi there"}),
    ]
    mock_redis.lrange.return_value = mock_messages
    manager = StateManager("localhost", 6379, 0)
    messages = manager.get_conversation("session-456")
    assert len(messages) == 2
    assert messages[0] == {"role": "user", "content": "Hello"}
    assert messages[1] == {"role": "assistant", "content": "Hi there"}
    mock_redis.lrange.assert_called_once_with("session:session-456:messages", 0, -1)


def test_add_message(mock_redis):
    manager = StateManager("localhost", 6379, 0)
    manager.add_message("session-789", "user", "Test message")
    expected_message = json.dumps({"role": "user", "content": "Test message"})
    mock_redis.rpush.assert_called_once_with("session:session-789:messages", expected_message)
    mock_redis.ltrim.assert_called_once_with("session:session-789:messages", -50, -1)


def test_add_message_assistant(mock_redis):
    manager = StateManager("localhost", 6379, 0)
    manager.add_message("session-abc", "assistant", "Response text")
    expected_message = json.dumps({"role": "assistant", "content": "Response text"})
    mock_redis.rpush.assert_called_once_with("session:session-abc:messages", expected_message)


def test_add_message_trims_to_50(mock_redis):
    manager = StateManager("localhost", 6379, 0)
    manager.add_message("session-trim", "user", "Msg")
    mock_redis.ltrim.assert_called_once_with("session:session-trim:messages", -50, -1)


def test_reset_session(mock_redis):
    manager = StateManager("localhost", 6379, 0)
    manager.reset_session("session-reset")
    mock_redis.delete.assert_called_once_with("session:session-reset:messages")


def test_reset_session_different_id(mock_redis):
    manager = StateManager("localhost", 6379, 0)
    manager.reset_session("another-session")
    mock_redis.delete.assert_called_once_with("session:another-session:messages")
