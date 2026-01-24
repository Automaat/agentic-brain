from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from .agent import BrainAgent
from .config import settings
from .mcp_client import MCPManager
from .state import StateManager


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    await mcp_manager.connect_all()
    yield


app = FastAPI(title="Brain Service", version="1.0.0", lifespan=lifespan)

state_manager = StateManager(settings.redis_host, settings.redis_port, settings.redis_db)
mcp_manager = MCPManager(settings.mcp_servers)
agent = BrainAgent(settings.anthropic_api_key, mcp_manager)


class ChatRequest(BaseModel):
    message: str
    interface: str = "api"
    language: str = "en"


class ChatResponse(BaseModel):
    response: str
    actions: list[str] = []


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: Annotated[str, Header()],
    session_id: Annotated[str, Header()],
) -> ChatResponse:
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
        return ChatResponse(response=response, actions=[])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/reset-session")
async def reset_session(session_id: Annotated[str, Header()]) -> dict[str, str]:
    state_manager.reset_session(session_id)
    return {"status": "reset", "session_id": session_id}
