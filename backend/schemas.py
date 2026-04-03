from pydantic import BaseModel, field_validator
from typing import Optional, Literal

# message from client to server
class IncomingMessage(BaseModel):
    type: Literal["message", "ping", "create_room", "join_room", "leave_room"]
    text: Optional[str] = None
    pin: Optional[str] = None
    
    @field_validator("text")
    @classmethod
    def text_not_blank(cls, input):
        if input is None and not input.strip():
            raise  ValueError("text must not be blank")
        return input.strip()