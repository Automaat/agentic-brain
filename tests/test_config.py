import os
from unittest.mock import patch

import pytest
from pydantic_core import ValidationError

from src.config import Settings


def test_settings_defaults():
    with patch.dict(
        os.environ,
        {
            "ANTHROPIC_API_KEY": "test-key",
            "HOMELAB_TAILSCALE_IP": "192.168.1.100",
        },
        clear=True,
    ):
        settings = Settings()  # type: ignore[call-arg]
        assert settings.anthropic_api_key == "test-key"
        assert settings.homelab_tailscale_ip == "192.168.1.100"
        assert settings.redis_host == "localhost"
        assert settings.redis_port == 6379
        assert settings.redis_db == 0
        assert settings.brain_host == "0.0.0.0"
        assert settings.brain_port == 8000
        assert settings.default_model == "claude-sonnet-4.5-20250929"
        assert settings.max_tokens == 4096
        assert settings.temperature == 0.7
        assert settings.todoist_api_token == ""


def test_settings_custom_values():
    with patch.dict(
        os.environ,
        {
            "ANTHROPIC_API_KEY": "custom-key",
            "TODOIST_API_TOKEN": "todoist-token",
            "HOMELAB_TAILSCALE_IP": "10.0.0.1",
            "REDIS_HOST": "redis-server",
            "REDIS_PORT": "6380",
            "REDIS_DB": "1",
            "BRAIN_HOST": "127.0.0.1",
            "BRAIN_PORT": "9000",
            "DEFAULT_MODEL": "claude-opus-4.5",
            "MAX_TOKENS": "8192",
            "TEMPERATURE": "0.5",
        },
        clear=True,
    ):
        settings = Settings()  # type: ignore[call-arg]
        assert settings.anthropic_api_key == "custom-key"
        assert settings.todoist_api_token == "todoist-token"
        assert settings.homelab_tailscale_ip == "10.0.0.1"
        assert settings.redis_host == "redis-server"
        assert settings.redis_port == 6380
        assert settings.redis_db == 1
        assert settings.brain_host == "127.0.0.1"
        assert settings.brain_port == 9000
        assert settings.default_model == "claude-opus-4.5"
        assert settings.max_tokens == 8192
        assert settings.temperature == 0.5


def test_mcp_servers_property():
    with patch.dict(
        os.environ,
        {
            "ANTHROPIC_API_KEY": "test-key",
            "HOMELAB_TAILSCALE_IP": "192.168.1.100",
        },
        clear=True,
    ):
        settings = Settings()  # type: ignore[call-arg]
        mcp_servers = settings.mcp_servers
        assert isinstance(mcp_servers, dict)
        assert len(mcp_servers) == 5
        assert mcp_servers["filesystem"] == "http://host.docker.internal:8001/sse"
        assert mcp_servers["shell"] == "http://host.docker.internal:8002/sse"
        assert mcp_servers["browser"] == "http://host.docker.internal:8003/sse"
        assert mcp_servers["homeassistant"] == "http://192.168.1.100:8010/sse"
        assert mcp_servers["todoist"] == "http://host.docker.internal:8011/sse"


def test_mcp_servers_uses_tailscale_ip():
    with patch.dict(
        os.environ,
        {
            "ANTHROPIC_API_KEY": "test-key",
            "HOMELAB_TAILSCALE_IP": "100.64.0.1",
        },
        clear=True,
    ):
        settings = Settings()  # type: ignore[call-arg]
        assert settings.mcp_servers["homeassistant"] == "http://100.64.0.1:8010/sse"


def test_settings_missing_required_field():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]
