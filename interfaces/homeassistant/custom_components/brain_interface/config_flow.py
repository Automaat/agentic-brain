"""Config flow for Brain Interface integration."""

import logging
from typing import Any

import httpx
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_BRAIN_URL,
    CONF_LANGUAGE,
    CONF_SESSION_PREFIX,
    CONF_USER_ID,
    DEFAULT_BRAIN_URL,
    DEFAULT_LANGUAGE,
    DEFAULT_SESSION_PREFIX,
    DOMAIN,
    SUPPORTED_LANGUAGES,
)

_LOGGER = logging.getLogger(__name__)


class BrainInterfaceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Brain Interface."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate brain URL is reachable
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{user_input[CONF_BRAIN_URL]}/health", timeout=5.0)
                    response.raise_for_status()

                # Create entry
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, "Brain Interface"),
                    data=user_input,
                )
            except (httpx.HTTPError, httpx.TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during brain service validation")
                errors["base"] = "unknown"

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default="Brain Interface"): str,
                    vol.Required(CONF_BRAIN_URL, default=DEFAULT_BRAIN_URL): str,
                    vol.Required(CONF_USER_ID): str,
                    vol.Optional(CONF_SESSION_PREFIX, default=DEFAULT_SESSION_PREFIX): str,
                    vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(SUPPORTED_LANGUAGES),
                }
            ),
            errors=errors,
        )
