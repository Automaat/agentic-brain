import json
from typing import Any

import redis

from .retry import retry_on_network_error

# Redis-specific retry decorator with appropriate parameters
retry_redis = retry_on_network_error(max_attempts=3, min_wait_seconds=1, max_wait_seconds=5)


class StateManager:
    def __init__(self, host: str, port: int, db: int):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    @retry_redis
    def get_conversation(self, session_id: str) -> list[dict[str, Any]]:
        messages = self.redis.lrange(f"session:{session_id}:messages", 0, -1)
        return [json.loads(msg) for msg in messages]

    @retry_redis
    def add_message(self, session_id: str, role: str, content: str) -> None:
        message = {"role": role, "content": content}
        self.redis.rpush(f"session:{session_id}:messages", json.dumps(message))
        self.redis.ltrim(f"session:{session_id}:messages", -50, -1)

    @retry_redis
    def reset_session(self, session_id: str) -> None:
        self.redis.delete(f"session:{session_id}:messages")
