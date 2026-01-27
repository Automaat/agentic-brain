# Agentic Brain

Production-ready modular AI assistant with centralized brain service and pluggable interfaces.

## Features

- **LangGraph Agent**: Agentic loop with Claude Sonnet 4.5
- **MCP Integration**: Model Context Protocol for tool calling
- **Multiple Interfaces**: Telegram, Home Assistant voice, REST API
- **Structured Logging**: JSON logs with request tracking
- **Retry Logic**: Automatic retries with exponential backoff
- **Prometheus Metrics**: Production monitoring support
- **Health Checks**: Detailed component status
- **Redis State**: Persistent conversation history

## Quick Start

```bash
# Setup
mise run setup

# Start
mise run build
mise run up

# Test
mise run health
mise run chat
```

## Architecture

Central "brain" service with pluggable interfaces:

```
┌─────────────────────────────────────┐
│     INTERFACES (Pluggable)          │
│  ┌──────────┐    ┌──────────┐      │
│  │Telegram  │    │  Home    │      │
│  │  Bot     │    │Assistant │      │
│  └────┬─────┘    └────┬─────┘      │
│       │               │             │
│       └───────┬───────┘             │
└───────────────┼─────────────────────┘
                ↓
┌─────────────────────────────────────┐
│      BRAIN SERVICE (Docker)         │
│  FastAPI → LangGraph → Claude API   │
│         ↓                           │
│  MCP Client → Tool Servers          │
│         ↓                           │
│  Redis (State Management)           │
└─────────────────────────────────────┘
```

**Components:**
- **Brain Service** (Docker): FastAPI + LangGraph + Claude API + MCP
- **Telegram Bot** (Mac): Text interface
- **Home Assistant** (Homelab): Voice interface
- **Redis** (Native): Conversation state

See [plan.md](plan.md) for architecture details.

## Production Features

### Structured Logging

JSON-formatted logs with request tracking:

```bash
# Configure via environment
LOG_LEVEL=INFO
LOG_JSON=true
```

All logs include:
- Request ID correlation
- Component name
- Timestamp (ISO format)
- Structured context

### Retry Logic

Automatic retries with exponential backoff for:
- MCP tool calls (3 attempts, 1-10s backoff)
- Claude API calls (3 attempts, 2-30s backoff)
- Redis operations (3 attempts, 1-5s backoff)

### Monitoring

Prometheus metrics endpoint: `GET /metrics`

Available metrics:
- `http_requests_total` - HTTP request counts by method/endpoint/status
- `http_request_duration_seconds` - Request latencies
- `chat_requests_total` - Chat requests by interface/language
- `chat_duration_seconds` - Chat processing time
- `chat_errors_total` - Chat errors by type
- `mcp_tool_calls_total` - MCP tool calls by server/tool/status
- `mcp_tool_duration_seconds` - Tool call latencies
- `mcp_servers_connected` - Connected MCP servers count

### Health Checks

Enhanced health endpoint: `GET /health`

Returns:
- Overall status (healthy/degraded/unhealthy)
- Redis connectivity
- MCP server status with tool counts
- Component-level details

Example response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "redis": {
      "status": "healthy",
      "message": "Connected"
    },
    "mcp_servers": {
      "status": "healthy",
      "healthy": 5,
      "total": 5,
      "servers": {
        "filesystem": {"status": "healthy", "tool_count": 12},
        "shell": {"status": "healthy", "tool_count": 5}
      }
    }
  }
}
```

## Development

```bash
mise run logs      # View logs
mise run test      # Run tests
mise run lint      # Run linters
mise run format    # Format code
mise run stats     # Resource usage
```

## Interfaces

### Telegram Bot

```bash
# Setup
mise run telegram:install
cd interfaces/telegram
cp .env.example .env
# Edit .env with your bot token

# Run
mise run telegram:start

# Auto-start on macOS
mise run telegram:install-service
mise run telegram:service:start
```

See [interfaces/telegram/README.md](interfaces/telegram/README.md) for details.

### Home Assistant

Custom component for voice conversation integration.

```bash
# Install
cp -r interfaces/homeassistant/custom_components/brain_interface \
  /path/to/homeassistant/config/custom_components/

# Configure via HA UI
# Settings → Devices & Services → Add Integration → Brain Interface
```

See [interfaces/homeassistant/README.md](interfaces/homeassistant/README.md) for details.

## API Reference

### POST /chat

Chat with the brain service.

**Headers:**
- `user_id` (required): User identifier
- `session_id` (required): Session identifier

**Body:**
```json
{
  "message": "Hello, how are you?",
  "interface": "telegram",
  "language": "en"
}
```

**Response:**
```json
{
  "response": "Hello! I'm doing well, thank you for asking.",
  "actions": []
}
```

### POST /reset-session

Reset conversation history.

**Headers:**
- `session_id` (required): Session to reset

**Response:**
```json
{
  "status": "reset",
  "session_id": "abc123"
}
```

### GET /health

Detailed health check (see Production Features above).

### GET /metrics

Prometheus metrics in text format.

## Environment Variables

Create `.env` file:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
HOMELAB_TAILSCALE_IP=100.x.y.z

# Optional
TODOIST_API_TOKEN=...
REDIS_HOST=host.docker.internal
REDIS_PORT=6379
LOG_LEVEL=INFO
LOG_JSON=true
```

## MCP Servers

The brain connects to MCP servers for tool access:

- **filesystem**: File operations (port 8001)
- **shell**: Command execution (port 8002)
- **browser**: Web automation (port 8003)
- **homeassistant**: Home control (port 8010)
- **todoist**: Task management (port 8011)

See [plan.md](plan.md) for MCP server setup.

## Troubleshooting

### Brain won't start
```bash
mise run logs           # Check logs
redis-cli ping          # Test Redis
docker compose down     # Clean restart
mise run build && mise run up
```

### MCP servers unreachable
```bash
lsof -i :8001           # Check if server running
curl http://localhost:8001/sse  # Test connectivity
```

### High memory usage
```bash
mise run stats          # Check usage
# Adjust docker-compose.yml resource limits
```

### View detailed logs
```bash
mise run logs           # Follow all logs
docker compose logs brain --tail 100  # Last 100 lines
```

## Requirements

- OrbStack or Docker
- Redis (native via Homebrew)
- mise
- Python 3.12+
- MCP servers (optional, for tool access)
