"""Tests for Prometheus metrics."""

from src.metrics import (
    active_sessions,
    chat_duration_seconds,
    chat_errors_total,
    chat_requests_total,
    get_metrics,
    http_request_duration_seconds,
    http_requests_total,
    mcp_servers_connected,
    mcp_tool_calls_total,
    mcp_tool_duration_seconds,
    model_api_calls_total,
    model_api_duration_seconds,
    redis_operations_total,
)


def test_get_metrics() -> None:
    """Test metrics generation returns valid Prometheus format."""
    # Increment some metrics
    http_requests_total.labels(method="GET", endpoint="/health", status="200").inc()
    chat_requests_total.labels(interface="telegram", language="en").inc()
    mcp_tool_calls_total.labels(server="test", tool="test_tool", status="success").inc()
    model_api_calls_total.labels(model="claude-3-opus").inc()
    redis_operations_total.labels(operation="set", status="success").inc()
    active_sessions.set(5)
    mcp_servers_connected.set(3)

    # Record histogram observations
    http_request_duration_seconds.labels(method="POST", endpoint="/chat").observe(0.5)
    chat_duration_seconds.labels(interface="telegram").observe(1.2)
    mcp_tool_duration_seconds.labels(server="test", tool="test_tool").observe(0.3)
    model_api_duration_seconds.labels(model="claude-3-opus").observe(2.1)

    # Record error
    chat_errors_total.labels(interface="telegram", error_type="timeout").inc()

    # Get metrics
    metrics = get_metrics()

    assert isinstance(metrics, bytes)
    metrics_str = metrics.decode("utf-8")

    # Verify key metrics are present
    assert "http_requests_total" in metrics_str
    assert "chat_requests_total" in metrics_str
    assert "mcp_tool_calls_total" in metrics_str
    assert "model_api_calls_total" in metrics_str
    assert "redis_operations_total" in metrics_str
    assert "active_sessions" in metrics_str
    assert "mcp_servers_connected" in metrics_str
    assert "http_request_duration_seconds" in metrics_str
    assert "chat_duration_seconds" in metrics_str
    assert "mcp_tool_duration_seconds" in metrics_str
    assert "model_api_duration_seconds" in metrics_str
    assert "chat_errors_total" in metrics_str


def test_metrics_are_singletons() -> None:
    """Test that metrics are module-level singletons."""
    from src import metrics

    # Verify metrics are the same instances
    assert metrics.http_requests_total is http_requests_total
    assert metrics.chat_requests_total is chat_requests_total
    assert metrics.mcp_tool_calls_total is mcp_tool_calls_total
    assert metrics.active_sessions is active_sessions
