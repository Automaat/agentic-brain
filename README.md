# Agentic Brain

Modular AI Assistant - Dockerized Brain Service

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

- **Brain Service** (Docker): FastAPI + LangGraph + Claude API + MCP
- **Telegram Bot** (Mac): Text interface
- **Home Assistant** (Homelab): Voice interface

See [plan.md](plan.md) for full details.

## Development

```bash
mise run logs      # View logs
mise run test      # Run tests
mise run lint      # Run linters
mise run format    # Format code
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

## Requirements

- OrbStack or Docker
- Redis (native via Homebrew)
- mise
- Python 3.12+
