import json
from typing import Any

import redis
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class StateManager:
    def __init__(self, host: str, port: int, db: int):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((redis.ConnectionError, redis.TimeoutError)),
        reraise=True,
    )
    def get_conversation(self, session_id: str) -> list[dict[str, Any]]:
        messages = self.redis.lrange(f"session:{session_id}:messages", 0, -1)
        return [json.loads(msg) for msg in messages]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((redis.ConnectionError, redis.TimeoutError)),
        reraise=True,
    )
    def add_message(self, session_id: str, role: str, content: str) -> None:
        message = {"role": role, "content": content}
        self.redis.rpush(f"session:{session_id}:messages", json.dumps(message))
        self.redis.ltrim(f"session:{session_id}:messages", -50, -1)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((redis.ConnectionError, redis.TimeoutError)),
        reraise=True,
    )
    def reset_session(self, session_id: str) -> None:
        self.redis.delete(f"session:{session_id}:messages")
