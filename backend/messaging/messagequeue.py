import os
from messaging.queuedmessage import QueuedMessage

from redis.asyncio import Redis

class MessageQueue:
    def __init__(self, redis_url: str | None=None, queue_key: str | None=None):
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self.queue_key = queue_key or os.getenv("MESSAGE_QUEUE_KEY", "chatapp:messages")
        self._redis = Redis.from_url(self.redis_url, decode_responses=True)
        
    async def ping(self) -> bool:
        return bool(await self._redis.ping())
    
    async def close(self) -> None:
        await self._redis.aclose()