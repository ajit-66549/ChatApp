import os
import asyncio
import redis
from celery import Celery
from pydantic import ValidationError
from database import CelerySessionLocal
from messaging.queuedmessage import QueuedMessage
from repositories import MessageRepository
from typing import Sequence
import logging

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MESSAGE_QUEUE_KEY = os.getenv("MESSAGE_QUEUE_KEY", "chatapp:messages")
MESSAGE_BATCH_SIZE = int(os.getenv("MESSAGE_BATCH_SIZE", "50"))
MESSAGE_FLUSH_SECONDS = float(os.getenv("MESSAGE_FLUSH_SECONDS", "5.0"))

logger = logging.getLogger(__name__)

#celery setup
celery_app = Celery(
    "celery_worker",
    broker=os.getenv("CELERY_BROKER_URL", REDIS_URL),
    backend=os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
)

celery_app.conf.worker_pool = "solo"  # Prevent forking issues with asyncio
celery_app.conf.beat_schedule = {
    "flush-message-queue": {
        "task": "messaging.worker.flush_message_queue",
        "schedule": MESSAGE_FLUSH_SECONDS,
    }
}
celery_app.conf.timezone = "UTC"

#connect with redis
def redis_client() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)

def pop_batch(client: redis.Redis, batch_size: int) -> list[str]:
    raw_messages: list[str] = []
    while len(raw_messages) < batch_size:
        popped = client.lpop(MESSAGE_QUEUE_KEY, batch_size - len(raw_messages))
        if not popped:
            break
        if isinstance(popped, list):
            raw_messages.extend(popped)
        else:
            raw_messages.append(popped)
    return raw_messages
    
def parse_messages(raw_messages: Sequence[str]) -> list[QueuedMessage]:
    messages: list[QueuedMessage] = []
    for message in raw_messages:
        try:
            messages.append(QueuedMessage.model_validate_json(message))
        except ValidationError:
            logger.exception("Dropping invalid queued message payload")
    return messages

async def persist_messages(messages: Sequence[QueuedMessage]) -> int:
    async with CelerySessionLocal() as session:
        repo = MessageRepository(session)
        return await repo.save_messages_batch(messages)

@celery_app.task(name="messaging.worker.flush_message_queue")
def flush_message_queue(batch_size: int | None=None) -> int:
    batch_size = batch_size or MESSAGE_BATCH_SIZE
    client = redis_client()
    try:
        raw_messages = pop_batch(client, batch_size)
        if not raw_messages:
            return 0

        messages = parse_messages(raw_messages)
        if not messages:
            return 0

        try:
            inserted_count = asyncio.run(persist_messages(messages))
            logger.info("Inserted %s queued messages", inserted_count)
            return inserted_count
        except Exception:
            logger.exception("Failed to persist message batch; requeueing messages")
            client.rpush(MESSAGE_QUEUE_KEY, *raw_messages)
            return 0
    except Exception:
        logger.exception("Error in flush_message_queue")
        return 0
    finally:
        client.close()