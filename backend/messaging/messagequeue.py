import os
from typing import Iterable
from messaging.queuedmessage import QueuedMessage

import redis.asyncio as redis

class MessageQueue:
    def __init__(self, redis_url: str | None=None, queue_key: str | None=None):
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self.queue_key = queue_key or os.getenv("MESSAGE_QUEUE_KEY", "chatapp:messages")
        self._redis = redis.from_url(self.redis_url, decode_responses=True)
        
    async def ping(self) -> bool:
        return bool(await self._redis.ping())
    
    async def enqueue(self, message: QueuedMessage) -> None:
        return self._redis.rpush(self.queue_key, message.model_dump_json())   # serialize message and rpush in queue
    
    async def enqueue_many(self, messages: Iterable[QueuedMessage]) -> None:
        payloads = [message.model_dump_json() for message in messages]
        if payloads:
            return self._redis_rpush(self.queue_key, *payloads)
    
    async def close(self) -> None:
        await self._redis.aclose()