"""Conversation platform for Brain Interface."""

import logging
import uuid
from typing import Literal

import httpx
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BRAIN_URL,
    CONF_LANGUAGE,
    CONF_SESSION_PREFIX,
    CONF_USER_ID,
    DEFAULT_LANGUAGE,
)
from .translations import get_message

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Brain conversation agent from a config entry."""
    agent = BrainConversationAgent(hass, entry)
    async_add_entities([agent])
    conversation.async_set_agent(hass, entry, agent)


class BrainConversationAgent(conversation.ConversationEntity):
    """Brain conversation agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self._attr_name = entry.data.get("name", "Brain Interface")
        self._attr_unique_id = entry.entry_id
        self._http_client = httpx.AsyncClient(timeout=30.0)

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return supported languages."""
        return ["en", "pl"]

    async def async_process(self, user_input: conversation.ConversationInput) -> conversation.ConversationResult:
        """Process a sentence."""
        config = self.entry.data
        brain_url = config[CONF_BRAIN_URL]
        user_id = config[CONF_USER_ID]
        session_prefix = config.get(CONF_SESSION_PREFIX, "ha")
        language = user_input.language if user_input.language != "*" else config.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)

        # Build session ID from conversation ID (generate UUID if None)
        conversation_id = user_input.conversation_id or str(uuid.uuid4())
        session_id = f"{session_prefix}_{conversation_id}"

        try:
            # Call brain API
            response = await self._http_client.post(
                f"{brain_url}/chat",
                json={
                    "message": user_input.text,
                    "interface": "voice",
                    "language": language,
                },
                headers={
                    "user_id": user_id,
                    "session_id": session_id,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Extract response text
            response_text = data.get("response", get_message(language, "no_response"))

            _LOGGER.debug(
                "Brain response for session %s: %s",
                session_id,
                response_text[:100],
            )

            return conversation.ConversationResult(
                response=conversation.ConversationResponse(
                    speech={"plain": {"speech": response_text}},
                    language=language,
                ),
                conversation_id=conversation_id,
            )

        except httpx.HTTPError as err:
            _LOGGER.error("Error calling brain API: %s", err)
            return conversation.ConversationResult(
                response=conversation.ConversationResponse(
                    speech={"plain": {"speech": get_message(language, "connection_error")}},
                    language=language,
                ),
                conversation_id=conversation_id,
            )

    async def async_will_remove_from_hass(self) -> None:
        """Close HTTP client when entity is removed."""
        await self._http_client.aclose()
