#!/usr/bin/env python3
"""Telegram bot interface for Brain Service"""

import asyncio
import logging
from typing import Any

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .config import settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class BrainTelegramBot:
    """Telegram bot that forwards messages to Brain Service"""

    def __init__(self, token: str, brain_url: str, allowed_user_ids: list[int] | None = None):
        self.token = token
        self.brain_url = brain_url
        self.allowed_user_ids = set(allowed_user_ids) if allowed_user_ids else None
        self.http_client = httpx.AsyncClient(timeout=60.0)

    def _is_user_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to use the bot"""
        if not self.allowed_user_ids:
            return True
        return user_id in self.allowed_user_ids

    async def _call_brain(
        self,
        message: str,
        user_id: str,
        session_id: str,
        language: str = "en",
    ) -> dict[str, Any]:
        """Call Brain Service API"""
        try:
            response = await self.http_client.post(
                f"{self.brain_url}/chat",
                json={"message": message, "interface": "telegram", "language": language},
                headers={"user_id": user_id, "session_id": session_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Brain API error: {e}")
            raise

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        if not update.effective_user:
            return

        user_id = update.effective_user.id
        if not self._is_user_allowed(user_id):
            await update.message.reply_text("Sorry, you are not authorized to use this bot.")  # type: ignore[union-attr]
            return

        welcome_text = """👋 Hello! I'm your AI assistant.

I can help you with:
• Answering questions
• Managing tasks
• Controlling smart home devices
• Browsing the web
• And much more!

Just send me a message to get started.

Commands:
/start - Show this message
/reset - Reset conversation
/lang - Change language (en/pl)
"""
        await update.message.reply_text(welcome_text)  # type: ignore[union-attr]

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reset command"""
        if not update.effective_user:
            return

        user_id = update.effective_user.id
        if not self._is_user_allowed(user_id):
            return

        session_id = f"telegram_{user_id}"
        try:
            await self.http_client.post(
                f"{self.brain_url}/reset-session",
                headers={"session_id": session_id},
            )
            await update.message.reply_text("✨ Conversation reset! Starting fresh.")  # type: ignore[union-attr]
        except httpx.HTTPError as e:
            logger.error(f"Reset error: {e}")
            await update.message.reply_text("❌ Failed to reset conversation. Please try again.")  # type: ignore[union-attr]

    async def lang_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /lang command"""
        if not update.effective_user:
            return

        user_id = update.effective_user.id
        if not self._is_user_allowed(user_id):
            return

        args = context.args
        if not args or args[0] not in ["en", "pl"]:
            await update.message.reply_text("Usage: /lang <en|pl>")  # type: ignore[union-attr]
            return

        language = args[0]
        context.user_data["language"] = language  # type: ignore[index]

        messages = {"en": "✅ Language set to English", "pl": "✅ Język ustawiony na polski"}
        await update.message.reply_text(messages[language])  # type: ignore[union-attr]

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular messages"""
        if not update.effective_user or not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        if not self._is_user_allowed(user_id):
            return

        # Show typing indicator
        await update.message.chat.send_action("typing")

        # Get language preference
        language = context.user_data.get("language", settings.default_language)  # type: ignore[union-attr]

        # Prepare request
        user_id_str = str(user_id)
        session_id = f"telegram_{user_id}"
        message_text = update.message.text

        try:
            # Call brain service
            result = await self._call_brain(
                message=message_text,
                user_id=user_id_str,
                session_id=session_id,
                language=language,
            )

            # Send response
            response_text = result.get("response", "I couldn't generate a response.")
            await update.message.reply_text(response_text)

        except httpx.HTTPError:
            error_messages = {
                "en": "❌ Sorry, I encountered an error. Please try again.",
                "pl": "❌ Przepraszam, wystąpił błąd. Spróbuj ponownie.",
            }
            await update.message.reply_text(error_messages.get(language, error_messages["en"]))

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        logger.error(f"Update {update} caused error: {context.error}")

    def build_application(self) -> Application:
        """Build and configure the bot application"""
        application = Application.builder().token(self.token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("reset", self.reset_command))
        application.add_handler(CommandHandler("lang", self.lang_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Error handler
        application.add_error_handler(self.error_handler)

        return application

    async def close(self) -> None:
        """Close HTTP client"""
        await self.http_client.aclose()


async def main() -> None:
    """Main entry point"""
    bot = BrainTelegramBot(
        token=settings.telegram_bot_token,
        brain_url=settings.brain_api_url,
        allowed_user_ids=settings.allowed_user_ids,
    )

    application = bot.build_application()

    logger.info("Starting Telegram bot...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()  # type: ignore[union-attr]

    logger.info("Bot is running. Press Ctrl+C to stop.")

    # Keep running until interrupted
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
    finally:
        await application.updater.stop()  # type: ignore[union-attr]
        await application.stop()
        await application.shutdown()
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
