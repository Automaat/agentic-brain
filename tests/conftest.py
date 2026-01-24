import os

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("HOMELAB_TAILSCALE_IP", "127.0.0.1")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
