# Telegram Bot Interface

Telegram bot interface for Brain Service.

## Setup

### 1. Create Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token

### 2. Configure

```bash
cd interfaces/telegram
cp .env.example .env
# Edit .env with your bot token
```

### 3. Install Dependencies

```bash
# From project root
mise run telegram:install
```

### 4. Run Bot

```bash
# Option 1: Using mise (recommended)
mise run telegram:start

# Option 2: Direct Python
cd interfaces/telegram
python -m .
```

## Usage

Start a chat with your bot on Telegram:

- `/start` - Show welcome message
- `/reset` - Reset conversation history
- `/lang en` - Set language to English
- `/lang pl` - Set language to Polish
- Send any message to chat with the AI

## Security

To restrict access to specific users:

1. Get your Telegram user ID (send `/start` to [@userinfobot](https://t.me/userinfobot))
2. Add to `.env`: `ALLOWED_USER_IDS=123456789,987654321`
3. Restart bot

## Auto-start on macOS

Create LaunchAgent (optional):

```bash
mise run telegram:install-service
```

This creates `~/Library/LaunchAgents/com.agentic-brain.telegram-bot.plist`

Control:
```bash
mise run telegram:service:start
mise run telegram:service:stop
mise run telegram:service:status
```

## Architecture

```
User (Telegram) → Bot → Brain Service (localhost:8000) → Claude API
                                ↓
                            Redis (state)
                                ↓
                         MCP Servers (tools)
```

## Development

Run with auto-reload:
```bash
cd interfaces/telegram
python -m .
```

View logs:
```bash
mise run telegram:logs
```
