# Brain Interface - Home Assistant Integration

Custom Home Assistant component for connecting to the Brain service.

## Features

- Voice conversation integration
- Multi-language support (English, Polish)
- Session persistence via Brain service
- Works with HA's Assist/Wyoming pipeline

## Installation

### Method 1: Manual

1. Copy the `custom_components/brain_interface` directory to your Home Assistant `config/custom_components/` directory:
   ```bash
   cp -r custom_components/brain_interface /path/to/homeassistant/config/custom_components/
   ```

2. Restart Home Assistant

3. Add integration via UI:
   - Settings → Devices & Services → Add Integration
   - Search for "Brain Interface"
   - Configure with your Brain service URL

### Method 2: Via Custom Repository (HACS)

Not yet available in HACS.

## Configuration

### Integration Setup

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| Integration Name | No | Brain Interface | Display name |
| Brain Service URL | Yes | `http://100.64.0.1:8000` | URL to Brain service (use Tailscale IP for homelab) |
| User ID | Yes | - | Unique identifier for the user |
| Session Prefix | No | `ha` | Prefix for session IDs (allows multi-interface sessions) |
| Default Language | No | `pl` | Language code (`en` or `pl`) |

### Example Configuration

For a homelab setup with Tailscale:
- **Brain Service URL**: `http://100.64.0.1:8000` (your Mac's Tailscale IP)
- **User ID**: `homeassistant_user`
- **Session Prefix**: `ha`
- **Language**: `pl`

## Usage

### Voice Assistant

1. Configure a voice assistant in Home Assistant (Assist)
2. Set "Brain Interface" as the conversation agent
3. Use voice commands: "Hey Home Assistant, turn on the lights"
4. The Brain service will process requests and can use MCP tools (Home Assistant control, filesystem, etc.)

### Automation

Use the conversation integration in automations:

```yaml
service: conversation.process
data:
  text: "What's the weather today?"
  agent_id: "conversation.brain_interface"
```

## Architecture

```
┌─────────────────────────────────────────────┐
│  Home Assistant (Homelab)                   │
│  ┌───────────────────────────────────────┐  │
│  │  Voice Input (Wyoming/Whisper)        │  │
│  │           ↓                            │  │
│  │  Brain Interface Component            │  │
│  │           ↓                            │  │
│  │  POST http://MAC_IP:8000/chat         │  │
│  │  (Tailscale connection)               │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Brain Service (Mac Docker)                 │
│  - LangGraph Agent                          │
│  - Claude API                               │
│  - MCP Tools (HA, filesystem, shell, etc.)  │
│  - Redis State                              │
└─────────────────────────────────────────────┘
```

## Session Management

Sessions are automatically created based on conversation IDs:
- Format: `{session_prefix}_{conversation_id}`
- Example: `ha_01HQWXYZ123ABC`
- Conversation history persisted in Redis (50 messages)
- Reset sessions via Brain API if needed

## Troubleshooting

### Cannot Connect to Brain Service

1. Check Brain service is running:
   ```bash
   curl http://YOUR_MAC_IP:8000/health
   ```

2. Verify Tailscale connectivity:
   ```bash
   ping YOUR_MAC_TAILSCALE_IP
   ```

3. Check Home Assistant logs:
   - Settings → System → Logs
   - Filter by "brain_interface"

### Brain Responses Are Slow

- Normal latency: 2-5 seconds (includes Claude API call + MCP tool calls)
- Check Brain service resource usage: `docker stats brain-service`
- Review Brain logs: `docker compose logs -f brain`

### Language Not Working

- Ensure language code matches supported languages (`en`, `pl`)
- Check Brain service config has correct language handling
- Session language persists - reset session if changed

## Development

### Testing Locally

1. Start Brain service:
   ```bash
   cd ~/sideprojects/agentic-brain
   mise run up
   ```

2. Copy component to HA test instance:
   ```bash
   cp -r custom_components/brain_interface /path/to/ha-test/config/custom_components/
   ```

3. View logs:
   ```bash
   tail -f /path/to/ha-test/config/home-assistant.log | grep brain_interface
   ```

### Adding Features

The component is minimal by design. Add features by:
1. Extending Brain service capabilities (MCP tools, agent logic)
2. Modifying `conversation.py` for HA-specific integrations
3. Adding config options in `config_flow.py` if needed

## See Also

- [Brain Service Documentation](../../README.md)
- [Home Assistant Conversation Integration](https://www.home-assistant.io/integrations/conversation/)
- [Wyoming Protocol](https://github.com/rhasspy/wyoming)
