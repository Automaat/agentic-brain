"""Prometheus metrics for monitoring."""

from prometheus_client import Counter, Gauge, Histogram, generate_latest

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

# Chat metrics
chat_requests_total = Counter(
    "chat_requests_total",
    "Total chat requests",
    ["interface", "language"],
)

chat_duration_seconds = Histogram(
    "chat_duration_seconds",
    "Chat processing duration in seconds",
    ["interface"],
)

chat_errors_total = Counter(
    "chat_errors_total",
    "Total chat errors",
    ["interface", "error_type"],
)

# MCP metrics
mcp_tool_calls_total = Counter(
    "mcp_tool_calls_total",
    "Total MCP tool calls",
    ["server", "tool", "status"],
)

mcp_tool_duration_seconds = Histogram(
    "mcp_tool_duration_seconds",
    "MCP tool call duration in seconds",
    ["server", "tool"],
)

mcp_servers_connected = Gauge(
    "mcp_servers_connected",
    "Number of connected MCP servers",
)

# Model metrics
model_api_calls_total = Counter(
    "model_api_calls_total",
    "Total model API calls",
    ["model"],
)

model_api_duration_seconds = Histogram(
    "model_api_duration_seconds",
    "Model API call duration in seconds",
    ["model"],
)

# Redis metrics
redis_operations_total = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],
)

# Session metrics
active_sessions = Gauge(
    "active_sessions",
    "Number of active sessions",
)


def get_metrics() -> bytes:
    """Generate Prometheus metrics in text format.

    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest()
