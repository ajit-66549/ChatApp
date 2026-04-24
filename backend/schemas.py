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
        if input is not None and not input.strip():
            raise ValueError("text must not be blank")
        return input.strip() if input else None
    
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
        
class PaginatedMessages(BaseModel):
    messages: list[MessageResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
    
class SignupRequest(BaseModel):
    username: str
    password: str
    
    @field_validator("username")
    @classmethod
    def username_valid(cls, input):
        input = input.strip()
        
        if len(input) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(input) > 50:
            raise ValueError("Username must be at most 50 characters")
        if not input.isalnum():
            raise ValueError("Username must be alphanumeric")
        return input
    
    @field_validator("password")
    @classmethod
    def passowrd_valid(cls, input):
        if len(input) < 6:
            raise ValueError("Password must be at least 6 characters")
        return input
    
class SignupResponse(BaseModel):
    id: str
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        
class LoginRequest(BaseModel):
    username: str
    password: str
    
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str