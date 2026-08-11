from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid

def current_time() -> datetime:
    return datetime.now(timezone.utc)

class QueuedMessage(BaseModel):
    id: str = Field(default_factory=lambda: (str(uuid.uuid4())))
    text: str
    user_id: str
    room_id: str | None = None
    created_at: datetime = Field(default_factory=current_time)