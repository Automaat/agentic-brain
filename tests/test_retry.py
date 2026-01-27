"""Tests for retry utilities."""

import pytest

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
