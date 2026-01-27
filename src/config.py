from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    anthropic_api_key: str = ""
    todoist_api_token: str = ""
    homelab_tailscale_ip: str = ""

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def mcp_servers(self) -> dict[str, str]:
        servers = {
            "filesystem": "http://host.docker.internal:8001/sse",
            "shell": "http://host.docker.internal:8002/sse",
            "browser": "http://host.docker.internal:8003/sse",
            "todoist": "http://host.docker.internal:8011/mcp/sse",
        }
        if self.homelab_tailscale_ip:
            servers["homeassistant"] = f"http://{self.homelab_tailscale_ip}:8010/sse"
        return servers

    brain_host: str = "0.0.0.0"
    brain_port: int = 8000
    default_model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    temperature: float = 0.7

    llm_provider: Literal["anthropic", "ollama"] = "anthropic"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1:8b"

    log_level: str = "INFO"
    log_json: bool = True


settings = Settings()  # type: ignore[call-arg]
