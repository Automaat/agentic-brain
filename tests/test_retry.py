"""Tests for retry utilities."""

import httpx
import pytest
from anthropic import APIConnectionError, APITimeoutError, RateLimitError

from src.retry import retry_on_anthropic_error, retry_on_network_error


def test_retry_on_network_error_decorator_applied() -> None:
    """Test decorator can be applied to sync function."""

    @retry_on_network_error(max_attempts=3)
    def sync_func() -> str:
        return "success"

    result = sync_func()
    assert result == "success"


@pytest.mark.anyio
async def test_retry_on_network_error_async_success() -> None:
    """Test async function succeeds without retry."""
    call_count = 0

    @retry_on_network_error(max_attempts=3)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        return "success"

    result = await async_func()
    assert result == "success"
    assert call_count == 1


@pytest.mark.anyio
async def test_retry_on_network_error_async_with_retry() -> None:
    """Test async function retries on ConnectionError."""
    call_count = 0

    @retry_on_network_error(max_attempts=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Network error")
        return "success"

    result = await async_func()
    assert result == "success"
    assert call_count == 3


@pytest.mark.anyio
async def test_retry_on_network_error_async_exhausted() -> None:
    """Test async function exhausts retries and raises."""
    call_count = 0

    @retry_on_network_error(max_attempts=2, min_wait_seconds=0.01, max_wait_seconds=0.1)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        raise TimeoutError("Always fails")

    with pytest.raises(TimeoutError, match="Always fails"):
        await async_func()
    assert call_count == 2


def test_retry_on_anthropic_error_decorator_applied() -> None:
    """Test Anthropic decorator can be applied to sync function."""

    @retry_on_anthropic_error(max_attempts=3)
    def sync_func() -> str:
        return "success"

    result = sync_func()
    assert result == "success"


@pytest.mark.anyio
async def test_retry_on_anthropic_error_async_success() -> None:
    """Test Anthropic retry decorator with async function."""
    call_count = 0

    @retry_on_anthropic_error(max_attempts=3)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        return "success"

    result = await async_func()
    assert result == "success"
    assert call_count == 1


@pytest.mark.anyio
async def test_retry_on_anthropic_error_async_with_retry() -> None:
    """Test Anthropic retry decorator retries async function."""
    call_count = 0

    @retry_on_anthropic_error(max_attempts=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("API error")
        return "success"

    result = await async_func()
    assert result == "success"
    assert call_count == 3


@pytest.mark.anyio
async def test_retry_on_anthropic_error_async_exhausted() -> None:
    """Test Anthropic retry decorator exhausts async attempts."""
    call_count = 0

    @retry_on_anthropic_error(max_attempts=2, min_wait_seconds=0.01, max_wait_seconds=0.1)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Always fails")

    with pytest.raises(ConnectionError, match="Always fails"):
        await async_func()
    assert call_count == 2


@pytest.mark.anyio
async def test_retry_on_network_error_httpx_request_error() -> None:
    """Test network retry catches httpx.RequestError."""
    call_count = 0

    @retry_on_network_error(max_attempts=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise httpx.RequestError("Network failure", request=None)  # type: ignore
        return "success"

    result = await async_func()
    assert result == "success"
    assert call_count == 2


@pytest.mark.anyio
async def test_retry_on_network_error_httpx_timeout() -> None:
    """Test network retry catches httpx.TimeoutException."""
    call_count = 0

    @retry_on_network_error(max_attempts=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise httpx.TimeoutException("Request timeout", request=None)  # type: ignore
        return "success"

    result = await async_func()
    assert result == "success"
    assert call_count == 2


@pytest.mark.anyio
async def test_retry_on_network_error_non_retryable_exception() -> None:
    """Test network retry fails fast on non-retryable exceptions."""
    call_count = 0

    @retry_on_network_error(max_attempts=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("Not a network error")

    with pytest.raises(ValueError, match="Not a network error"):
        await async_func()
    assert call_count == 1  # Should not retry


def test_retry_on_network_error_sync_retries() -> None:
    """Test sync wrapper actually retries on network errors."""
    call_count = 0

    @retry_on_network_error(max_attempts=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
    def sync_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Sync network error")
        return "success"

    result = sync_func()
    assert result == "success"
    assert call_count == 3


@pytest.mark.anyio
async def test_retry_on_anthropic_error_api_connection_error() -> None:
    """Test Anthropic retry catches APIConnectionError."""
    call_count = 0

    @retry_on_anthropic_error(max_attempts=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise APIConnectionError(request=None)  # type: ignore
        return "success"

    result = await async_func()
    assert result == "success"
    assert call_count == 2


@pytest.mark.anyio
async def test_retry_on_anthropic_error_api_timeout_error() -> None:
    """Test Anthropic retry catches APITimeoutError."""
    call_count = 0

    @retry_on_anthropic_error(max_attempts=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise APITimeoutError(request=None)  # type: ignore
        return "success"

    result = await async_func()
    assert result == "success"
    assert call_count == 2


@pytest.mark.anyio
async def test_retry_on_anthropic_error_rate_limit_error() -> None:
    """Test Anthropic retry catches RateLimitError."""
    call_count = 0

    # Create mock response for RateLimitError
    import httpx

    mock_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    mock_response = httpx.Response(429, request=mock_request)

    @retry_on_anthropic_error(max_attempts=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
    async def async_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RateLimitError("Rate limited", response=mock_response, body=None)
        return "success"

    result = await async_func()
    assert result == "success"
    assert call_count == 2
