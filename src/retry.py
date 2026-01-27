"""Retry utilities with exponential backoff."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def retry_on_network_error(
    max_attempts: int = 3,
    min_wait_seconds: float = 1,
    max_wait_seconds: float = 10,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry on network/HTTP errors with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait_seconds: Minimum wait time between retries
        max_wait_seconds: Maximum wait time between retries

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait_seconds, max=max_wait_seconds),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            reraise=True,
            before_sleep=lambda retry_state: logger.warning(
                "Retrying after error",
                function=func.__name__,
                attempt=retry_state.attempt_number,
                error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
            ),
        )
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def retry_on_anthropic_error(
    max_attempts: int = 3,
    min_wait_seconds: float = 2,
    max_wait_seconds: float = 30,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry on Anthropic API errors with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait_seconds: Minimum wait time between retries
        max_wait_seconds: Maximum wait time between retries

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=2, min=min_wait_seconds, max=max_wait_seconds),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            reraise=True,
            before_sleep=lambda retry_state: logger.warning(
                "Retrying Anthropic API call",
                function=func.__name__,
                attempt=retry_state.attempt_number,
                error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
            ),
        )
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
