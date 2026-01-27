# Plan: Modular AI Assistant - Dockerized Brain Service

## Architecture Overview

**Separation of Concerns**: Central "brain" service with pluggable interfaces

```
┌─────────────────────────────────────────────────────────────────┐
│                     INTERFACES (Pluggable)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────┐            │
│  │ Home Assistant   │         │ Telegram Bot     │            │
│  │ (Voice)          │         │ (Text)           │            │
│  │ Homelab          │         │ Mac              │            │
│  └────────┬─────────┘         └────────┬─────────┘            │
│           │                            │                       │
│           │ POST /chat                 │ POST /chat            │
│           │ (Tailscale)                │ (localhost)           │
│           │                            │                       │
└───────────┼────────────────────────────┼───────────────────────┘
            │                            │
            └──────────────┬─────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BRAIN SERVICE (Mac)                          │
│                    Docker Container                             │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI (Port 8000) ← Volume mount ~/agentic-brain/src        │
│         ↓                                                       │
│  LangGraph Agent (Agentic Loop)                                │
│         ↓                                                       │
│  Claude Sonnet 4.5 API                                         │
│         ↓                                                       │
│  MCP Client → Local/Remote/Cloud MCP Servers                   │
│         ↓                                                       │
│  Redis (Homebrew, native) ← Conversation state                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principles**:
- **Brain**: Central intelligence, all MCP communication, state management
- **Interfaces**: Pluggable (HA voice, Telegram, future: Discord, web UI)
- **State**: Redis-backed conversation history per session
- **Transport**: HTTP REST API (simple, stateless interfaces)
- **Privacy**: Audio stays local (Whisper/Piper), only text to Claude API

## Quick Start

```bash
# Setup (one-time)
cd ~/sideprojects/agentic-brain
mise run setup

# Start brain
mise run build
mise run up

# Test
mise run health
mise run chat

# View logs
mise run logs
```

See [Mise Tasks Reference](#mise-tasks-reference) for all commands.

## Project Structure

```
~/sideprojects/agentic-brain/
├── Dockerfile              # Multi-stage build
├── docker-compose.yml      # Resource limits, volumes
├── .mise.toml             # Task runner
├── requirements.txt        # Python deps
├── .env                    # Secrets (gitignored)
├── .gitignore
├── src/                    # Source (volume mounted)
│   ├── main.py            # FastAPI
│   ├── agent.py           # LangGraph
│   ├── mcp_client.py      # MCP
│   ├── state.py           # Redis
│   └── config.py          # Settings
├── tests/
├── logs/                  # Gitignored
└── README.md
```

## Implementation

See full implementation details in sections below:
- [Dockerfile](#dockerfile)
- [Docker Compose](#docker-compose)
- [Source Code](#source-code)
- [MCP Servers](#mcp-servers-setup)
- [Interfaces](#pluggable-interfaces)

### Dockerfile

Multi-stage build for minimal image size (~200-300MB).

<details>
<summary>Click to expand Dockerfile</summary>

```dockerfile
# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY src/ ./src/

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

RUN useradd -m -u 1000 brain && chown -R brain:brain /app
USER brain

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

</details>

### Docker Compose

Resource limits: 1 CPU, 1GB RAM.

<details>
<summary>Click to expand docker-compose.yml</summary>

```yaml
version: '3.8'

services:
  brain:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: brain-service
    restart: unless-stopped

    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

    ports:
      - "8000:8000"

    volumes:
      - ./src:/app/src:ro
      - ./logs:/app/logs

    env_file:
      - .env
    environment:
      - REDIS_HOST=host.docker.internal
      - REDIS_PORT=6379
      - PYTHONUNBUFFERED=1

    extra_hosts:
      - "host.docker.internal:host-gateway"

    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
```

</details>

### Mise Configuration

Task runner (replaces Make).

<details>
<summary>Click to expand .mise.toml</summary>

```toml
[tools]
python = "3.12"

[tasks.setup]
description = "Initial setup"
run = """
brew install orbstack redis
brew services start redis
echo "Setup complete! Next: mise run build && mise run up"
"""

[tasks.build]
description = "Build Docker image"
run = "docker compose build"

[tasks.up]
description = "Start brain service"
run = """
docker compose up -d
echo "Brain: http://localhost:8000"
echo "Health: mise run health"
"""

[tasks.down]
description = "Stop brain"
run = "docker compose down"

[tasks.restart]
description = "Restart brain"
run = "docker compose restart brain"

[tasks.logs]
description = "View logs"
run = "docker compose logs -f brain"

[tasks.shell]
description = "Shell into container"
run = "docker compose exec brain /bin/bash"

[tasks.test]
description = "Run tests"
run = "docker compose exec brain pytest tests/ -v"

[tasks.clean]
description = "Remove containers/images"
run = """
docker compose down -v
docker image prune -f
"""

[tasks.health]
description = "Health check"
run = "curl -s http://localhost:8000/health | jq"

[tasks.chat]
description = "Test chat"
run = """
curl -X POST http://localhost:8000/chat \
  -H "user_id: test" \
  -H "session_id: test" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "interface": "api", "language": "en"}' | jq
"""

[tasks.stats]
description = "Resource usage"
run = "docker stats brain-service --no-stream"

[tasks.redis-cli]
description = "Redis CLI"
run = "redis-cli"
```

</details>

### Source Code

Core Python files implementing brain service.

<details>
<summary>Click to expand src/ files</summary>

**`src/config.py`** - Configuration management

```python
from pydantic_settings import BaseSettings
from typing import Dict

class Settings(BaseSettings):
    anthropic_api_key: str
    todoist_api_token: str = ""
    homelab_tailscale_ip: str

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def mcp_servers(self) -> Dict[str, str]:
        return {
            "filesystem": "http://host.docker.internal:8001/sse",
            "shell": "http://host.docker.internal:8002/sse",
            "browser": "http://host.docker.internal:8003/sse",
            "homeassistant": f"http://{self.homelab_tailscale_ip}:8010/sse",
            "todoist": "http://host.docker.internal:8011/sse",
        }

    brain_host: str = "0.0.0.0"
    brain_port: int = 8000
    default_model: str = "claude-sonnet-4.5-20250929"
    max_tokens: int = 4096
    temperature: float = 0.7

    class Config:
        env_file = ".env"

settings = Settings()
```

**`src/state.py`** - Redis state management

```python
import redis
import json
from typing import List, Dict, Any

class StateManager:
    def __init__(self, host: str, port: int, db: int):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        messages = self.redis.lrange(f"session:{session_id}:messages", 0, -1)
        return [json.loads(msg) for msg in messages]

    def add_message(self, session_id: str, role: str, content: str):
        message = {"role": role, "content": content}
        self.redis.rpush(f"session:{session_id}:messages", json.dumps(message))
        self.redis.ltrim(f"session:{session_id}:messages", -50, -1)

    def reset_session(self, session_id: str):
        self.redis.delete(f"session:{session_id}:messages")
```

**`src/main.py`** - FastAPI endpoints

```python
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import uvicorn

from .config import settings
from .state import StateManager
from .mcp_client import MCPManager
from .agent import BrainAgent

app = FastAPI(title="Brain Service", version="1.0.0")

state_manager = StateManager(settings.redis_host, settings.redis_port, settings.redis_db)
mcp_manager = MCPManager(settings.mcp_servers)
agent = BrainAgent(settings.anthropic_api_key, mcp_manager)

class ChatRequest(BaseModel):
    message: str
    interface: str = "api"
    language: str = "en"

class ChatResponse(BaseModel):
    response: str
    actions: list = []

@app.on_event("startup")
async def startup():
    await mcp_manager.connect_all()

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Header(...),
    session_id: str = Header(...)
):
    try:
        history = state_manager.get_conversation(session_id)
        state_manager.add_message(session_id, "user", request.message)

        response = await agent.chat(
            message=request.message,
            user_id=user_id,
            session_id=session_id,
            interface=request.interface,
            language=request.language
        )

        state_manager.add_message(session_id, "assistant", response)
        return ChatResponse(response=response, actions=[])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset-session")
async def reset_session(session_id: str = Header(...)):
    state_manager.reset_session(session_id)
    return {"status": "reset", "session_id": session_id}
```

**`src/agent.py`** - LangGraph agentic loop (TODO: implement)

**`src/mcp_client.py`** - MCP client (TODO: implement)

</details>

### Environment Variables

**`.env`** (gitignored):
```bash
ANTHROPIC_API_KEY=sk-ant-...
TODOIST_API_TOKEN=...
HOMELAB_TAILSCALE_IP=100.x.y.z
REDIS_HOST=host.docker.internal
REDIS_PORT=6379
```

## MCP Servers Setup

### Mac MCP Servers

MCP servers run on host machine, accessible from Docker container via `host.docker.internal`:

**Active servers:**
- Filesystem (port 8001): File operations on allowed directories
- Shell (port 8002): Command execution capabilities
- Browser (port 8003): Web automation and scraping
- Todoist (port 8011): Task management integration
- Home Assistant (port 8012): Smart home control (conditional)

**Configuration:** Servers use HTTP SSE protocol. See `src/mcp_client.py` for connection details.

**Port mappings:** All servers bind to `127.0.0.1:<port>` for Docker bridge access.

## Pluggable Interfaces

### 1. Home Assistant Voice (Homelab)

Custom HA component calls brain REST API.

**Flow**:
1. User speaks → Whisper STT → Polish text
2. `POST http://MAC_TAILSCALE_IP:8000/chat`
3. Brain responds → Piper TTS → audio

### 2. Telegram Bot (Mac)

Python bot calls brain locally.

**Flow**:
1. User sends Telegram message
2. `POST http://localhost:8000/chat`
3. Brain responds → Send message back

### 3. Future Interfaces

Add any interface - just call `POST /chat`. Examples:
- Discord bot
- Web UI
- Mobile app
- CLI tool

## API Contract

### POST /chat

**Request**:
```json
{
  "message": "Turn on lights",
  "interface": "voice|telegram|api",
  "language": "en|pl"
}
```

**Headers**:
```
user_id: string
session_id: string
```

**Response**:
```json
{
  "response": "Lights turned on",
  "actions": []
}
```

## Development Workflow

### Hot Reload
1. Edit `~/sideprojects/agentic-brain/src/main.py`
2. Uvicorn auto-reloads (volume mounted)
3. Test with `mise run chat`

### Add Dependencies
```bash
echo "new-package==1.0.0" >> requirements.txt
mise run build
mise run up
```

### Debug
```bash
mise run logs      # View logs
mise run shell     # Shell into container
mise run stats     # Resource usage
```

## Mise Tasks Reference

| Command | Description |
|---------|-------------|
| `mise run setup` | Install OrbStack, Redis |
| `mise run build` | Build Docker image |
| `mise run up` | Start brain service |
| `mise run down` | Stop service |
| `mise run restart` | Restart brain |
| `mise run logs` | View logs (follow) |
| `mise run health` | Health check |
| `mise run chat` | Test chat endpoint |
| `mise run shell` | Shell into container |
| `mise run test` | Run pytest |
| `mise run stats` | Resource usage |
| `mise run redis-cli` | Redis CLI |
| `mise run clean` | Remove containers |

## Resource Usage

**Expected** (OrbStack):
- Brain container: 500-700MB RAM
- Redis (native): 50MB RAM
- **Total: <1GB**

Monitor with: `mise run stats`

## Next Steps

### Week 1: Core Brain
1. `mise run setup`
2. Implement `src/agent.py` (LangGraph)
3. Implement `src/mcp_client.py`
4. Test with `mise run chat`

### Week 2: Interfaces
1. Create HA `brain_interface` component
2. Create Telegram bot
3. Test cross-interface state

### Week 3: Production
1. Error handling, retries
2. Logging, monitoring
3. Tests
4. Documentation

## Cost Estimate

**~$26-27/month**:
- Claude API: $25
- Mac power: $1-2

## Troubleshooting

**Brain won't start**:
```bash
mise run logs
redis-cli ping
mise run rebuild
```

**MCP servers unreachable**:
```bash
lsof -i :8001
curl http://localhost:8001/sse
```

**High memory**:
```bash
mise run stats
# Adjust docker-compose.yml limits
```

---

**Full details** available in collapsed sections above. Start with Quick Start, then review Implementation sections as needed.
