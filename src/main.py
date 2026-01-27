import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, Header, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST
from pydantic import BaseModel

from .agent import BrainAgent
from .config import settings
from .health import check_health
from .logging_config import get_logger, request_id_var, setup_logging
from .mcp_client import MCPManager
from .metrics import (
    chat_duration_seconds,
    chat_errors_total,
    chat_requests_total,
    get_metrics,
    http_request_duration_seconds,
    http_requests_total,
)
from .state import StateManager

setup_logging(log_level=settings.log_level, json_format=settings.log_json)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    logger.info("Starting Brain Service", version="1.0.0")
    await mcp_manager.connect_all()
    logger.info("MCP servers connected")
    yield
    logger.info("Shutting down Brain Service")
    await mcp_manager.close()


app = FastAPI(title="Brain Service", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):  # type: ignore
    """Add request ID to context and response headers."""
    request_id = str(uuid.uuid4())
    token = request_id_var.set(request_id)

    try:
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration = time.perf_counter() - start_time

        response.headers["X-Request-ID"] = request_id

        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )

        return response
    finally:
        request_id_var.reset(token)


state_manager = StateManager(settings.redis_host, settings.redis_port, settings.redis_db)
mcp_manager = MCPManager(settings.mcp_servers)
agent = BrainAgent(settings.anthropic_api_key, mcp_manager)


class ChatRequest(BaseModel):
    message: str
    interface: Literal["voice", "telegram", "api"] = "api"
    language: Literal["pl", "en"] = "en"


class ChatResponse(BaseModel):
    response: str
    actions: list[str] = []


@app.get("/health")
async def health():  # type: ignore
    """Detailed health check endpoint."""
    logger.debug("Health check requested")
    return await check_health(state_manager, mcp_manager)


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: Annotated[str, Header()],
    session_id: Annotated[str, Header()],
) -> ChatResponse:
    logger.info(
        "Chat request received",
        user_id=user_id,
        session_id=session_id,
        interface=request.interface,
        language=request.language,
        message_length=len(request.message),
    )

    # Record metrics
    chat_requests_total.labels(
        interface=request.interface,
        language=request.language,
    ).inc()

    start_time = time.perf_counter()

    try:
        history = state_manager.get_conversation(session_id)
        state_manager.add_message(session_id, "user", request.message)

        response = await agent.chat(
            message=request.message,
            history=history,
            user_id=user_id,
            session_id=session_id,
            interface=request.interface,
            language=request.language,
        )

        state_manager.add_message(session_id, "assistant", response)

        duration = time.perf_counter() - start_time
        chat_duration_seconds.labels(interface=request.interface).observe(duration)

        logger.info(
            "Chat response generated",
            user_id=user_id,
            session_id=session_id,
            response_length=len(response),
            duration_seconds=round(duration, 2),
        )

        return ChatResponse(response=response, actions=[])

    except Exception as e:
        chat_errors_total.labels(
            interface=request.interface,
            error_type=type(e).__name__,
        ).inc()

        logger.error(
            "Chat request failed",
            user_id=user_id,
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/reset-session")
async def reset_session(session_id: Annotated[str, Header()]) -> dict[str, str]:
    logger.info("Session reset requested", session_id=session_id)
    state_manager.reset_session(session_id)
    logger.info("Session reset completed", session_id=session_id)
    return {"status": "reset", "session_id": session_id}
