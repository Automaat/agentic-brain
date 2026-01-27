"""Health check utilities."""

from typing import Any

import redis

from .logging_config import get_logger
from .mcp_client import MCPManager
from .state import StateManager

logger = get_logger(__name__)


async def check_health(
    state_manager: StateManager,
    mcp_manager: MCPManager,
) -> dict[str, Any]:
    """Check health of all system components.

    Args:
        state_manager: Redis state manager
        mcp_manager: MCP server manager

    Returns:
        Health status dictionary with component details
    """
    health_status: dict[str, Any] = {
        "status": "healthy",
        "version": "1.0.0",
        "components": {},
    }

    # Check Redis
    redis_healthy = True
    redis_error = None
    try:
        state_manager.redis.ping()
        health_status["components"]["redis"] = {
            "status": "healthy",
            "message": "Connected",
        }
    except (redis.ConnectionError, redis.TimeoutError) as e:
        redis_healthy = False
        redis_error = str(e)
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": redis_error,
        }
        logger.error("Redis health check failed", error=redis_error)

    # Check MCP servers
    mcp_status: dict[str, dict[str, Any]] = {}
    mcp_healthy_count = 0
    mcp_total_count = len(mcp_manager.servers)

    for server_name in mcp_manager.servers:
        tool_count = len(mcp_manager.tools.get(server_name, []))
        if tool_count > 0:
            mcp_status[server_name] = {
                "status": "healthy",
                "tool_count": tool_count,
            }
            mcp_healthy_count += 1
        else:
            mcp_status[server_name] = {
                "status": "unhealthy",
                "message": "No tools discovered",
            }

    # Component status: healthy only if all healthy, degraded if partial, unhealthy if none
    if mcp_total_count == 0:
        mcp_component_status = "healthy"  # No servers configured - optional component
    elif mcp_healthy_count == mcp_total_count:
        mcp_component_status = "healthy"
    elif mcp_healthy_count > 0:
        mcp_component_status = "degraded"
    else:
        mcp_component_status = "unhealthy"

    health_status["components"]["mcp_servers"] = {
        "status": mcp_component_status,
        "healthy": mcp_healthy_count,
        "total": mcp_total_count,
        "servers": mcp_status,
    }

    # Overall health
    if not redis_healthy:
        health_status["status"] = "unhealthy"
    elif mcp_total_count > 0 and mcp_healthy_count < mcp_total_count:
        health_status["status"] = "degraded"

    return health_status
