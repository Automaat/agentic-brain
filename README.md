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

Central "brain" service with pluggable interfaces (HA voice, Telegram, etc.)

See [plan.md](plan.md) for full details.

## Development

```bash
mise run logs      # View logs
mise run test      # Run tests
mise run lint      # Run linters
mise run format    # Format code
```

## Requirements

- OrbStack or Docker
- Redis (native via Homebrew)
- mise
- Python 3.12+
