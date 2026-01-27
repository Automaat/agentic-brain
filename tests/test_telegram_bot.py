"""Tests for Telegram bot interface"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from telegram import Chat, Message, Update, User

from interfaces.telegram.bot import BrainTelegramBot


@pytest_asyncio.fixture
async def bot():
    """Create bot instance for testing"""
    bot_instance = BrainTelegramBot(
        token="test_token",
        brain_url="http://localhost:8000",
        allowed_user_ids=[12345],
    )
    try:
        yield bot_instance
    finally:
        await bot_instance.close()


@pytest.fixture
def mock_update():
    """Create mock Telegram update"""
    update = MagicMock(spec=Update)
    update.effective_user = User(id=12345, is_bot=False, first_name="Test")
    update.message = MagicMock(spec=Message)
    update.message.text = "Hello"
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.send_action = AsyncMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context"""
    context = MagicMock()
    context.user_data = {}
    context.args = []
    return context


class TestBrainTelegramBot:
    """Test BrainTelegramBot class"""

    def test_is_user_allowed_no_restrictions(self):
        """Test user authorization with no restrictions"""
        bot = BrainTelegramBot(token="test", brain_url="http://localhost", allowed_user_ids=None)
        assert bot._is_user_allowed(12345) is True
        assert bot._is_user_allowed(99999) is True

    def test_is_user_allowed_with_restrictions(self, bot):
        """Test user authorization with restrictions"""
        assert bot._is_user_allowed(12345) is True
        assert bot._is_user_allowed(99999) is False

    async def test_start_command_authorized(self, bot, mock_update, mock_context):
        """Test /start command for authorized user"""
        await bot.start_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Hello" in call_args
        assert "/start" in call_args

    async def test_start_command_unauthorized(self, bot, mock_update, mock_context):
        """Test /start command for unauthorized user"""
        mock_update.effective_user = User(id=99999, is_bot=False, first_name="Unauthorized")
        await bot.start_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "not authorized" in call_args

    async def test_reset_command_success(self, bot, mock_update, mock_context):
        """Test /reset command success"""
        with patch.object(bot.http_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            await bot.reset_command(mock_update, mock_context)
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "reset" in call_args.lower()

    async def test_reset_command_error(self, bot, mock_update, mock_context):
        """Test /reset command error handling"""
        with patch.object(bot.http_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Connection failed")
            await bot.reset_command(mock_update, mock_context)
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Failed" in call_args

    async def test_lang_command_english(self, bot, mock_update, mock_context):
        """Test /lang command to set English"""
        mock_context.args = ["en"]
        await bot.lang_command(mock_update, mock_context)
        assert mock_context.user_data["language"] == "en"
        mock_update.message.reply_text.assert_called_once()

    async def test_lang_command_polish(self, bot, mock_update, mock_context):
        """Test /lang command to set Polish"""
        mock_context.args = ["pl"]
        await bot.lang_command(mock_update, mock_context)
        assert mock_context.user_data["language"] == "pl"
        mock_update.message.reply_text.assert_called_once()

    async def test_lang_command_invalid(self, bot, mock_update, mock_context):
        """Test /lang command with invalid language"""
        mock_context.args = ["fr"]
        await bot.lang_command(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Usage" in call_args

    async def test_lang_command_no_args(self, bot, mock_update, mock_context):
        """Test /lang command with no arguments"""
        mock_context.args = []
        await bot.lang_command(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Usage" in call_args

    async def test_handle_message_success(self, bot, mock_update, mock_context):
        """Test successful message handling"""
        with patch.object(bot, "_call_brain", new_callable=AsyncMock) as mock_brain:
            mock_brain.return_value = {"response": "Hello! How can I help?", "actions": []}
            await bot.handle_message(mock_update, mock_context)

            # Verify typing indicator
            mock_update.message.chat.send_action.assert_called_once_with("typing")

            # Verify brain was called
            mock_brain.assert_called_once()
            call_kwargs = mock_brain.call_args[1]
            assert call_kwargs["message"] == "Hello"
            assert call_kwargs["user_id"] == "12345"
            assert call_kwargs["session_id"] == "telegram_12345"

            # Verify response sent
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "How can I help" in call_args

    async def test_handle_message_error(self, bot, mock_update, mock_context):
        """Test message handling with API error"""
        with patch.object(bot, "_call_brain", new_callable=AsyncMock) as mock_brain:
            mock_brain.side_effect = httpx.HTTPError("API error")
            await bot.handle_message(mock_update, mock_context)

            # Verify error message sent
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "error" in call_args.lower()

    async def test_handle_message_unauthorized(self, bot, mock_update, mock_context):
        """Test message handling for unauthorized user"""
        mock_update.effective_user = User(id=99999, is_bot=False, first_name="Unauthorized")
        await bot.handle_message(mock_update, mock_context)

        # Should not send any response
        mock_update.message.reply_text.assert_not_called()

    async def test_call_brain_success(self, bot):
        """Test successful brain API call"""
        with patch.object(bot.http_client, "post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "Test response", "actions": []}
            mock_post.return_value = mock_response

            result = await bot._call_brain(
                message="Test message",
                user_id="12345",
                session_id="test_session",
                language="en",
            )

            assert result == {"response": "Test response", "actions": []}
            mock_post.assert_called_once()

    async def test_call_brain_error(self, bot):
        """Test brain API call error"""
        with patch.object(bot.http_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Connection failed")

            with pytest.raises(httpx.HTTPError):
                await bot._call_brain(
                    message="Test",
                    user_id="123",
                    session_id="test",
                    language="en",
                )

    def test_build_application(self, bot):
        """Test application building"""
        app = bot.build_application()
        assert app is not None
        assert len(app.handlers) > 0
