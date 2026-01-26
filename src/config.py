from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    anthropic_api_key: str
    todoist_api_token: str = ""
    homelab_tailscale_ip: str

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def mcp_servers(self) -> dict[str, str]:
        return {
            "filesystem": "http://host.docker.internal:8001/sse",
            "shell": "http://host.docker.internal:8002/sse",
            "browser": "http://host.docker.internal:8003/sse",
            "homeassistant": f"http://{self.homelab_tailscale_ip}:8010/sse",
            "todoist": "http://host.docker.internal:8011/sse",
        }

    brain_host: str = "0.0.0.0"
    brain_port: int = 8000
    default_model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    temperature: float = 0.7


settings = Settings()  # type: ignore[call-arg]
