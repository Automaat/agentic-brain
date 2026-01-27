"""Brain Interface integration for Home Assistant."""

import logging

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_BRAIN_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CONVERSATION]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Brain Interface from a config entry."""
    brain_url = entry.data[CONF_BRAIN_URL]

    # Verify brain service is reachable
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{brain_url}/health", timeout=5.0)
            response.raise_for_status()
            _LOGGER.info("Connected to brain service at %s", brain_url)
    except (httpx.HTTPError, httpx.TimeoutError) as err:
        _LOGGER.error("Failed to connect to brain service: %s", err)
        raise ConfigEntryNotReady(f"Cannot connect to brain service: {err}") from err

    # Store config entry data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Forward setup to conversation platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
