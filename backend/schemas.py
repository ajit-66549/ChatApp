from pydantic import BaseModel, field_validator
from typing import Optional, Literal
from datetime import datetime

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
    
class UserResponse(BaseModel):
    id: str
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True     # allows SQLAlchemy models to pydantic model
        
class MessageResponse(BaseModel):
    id: str
    text: str
    user_id: str
    room_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
        
class PaginatedMessage(BaseModel):
    messages: list[MessageResponse]
    total: int
    limit: int
    offset: int
    has_more: bool