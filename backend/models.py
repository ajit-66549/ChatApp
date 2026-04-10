from sqlalchemy import (
    Column, String, Text, Boolean,
    DateTime, ForeignKey, Integer, func, Index
)
from sqlalchemy.orm import relationship
from database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

# database model for User
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    messages = relationship("Message", back_populates="user")
    
# databse model for Room
class Room(Base):
    __tablename__ = "rooms"
    id = Column(String, primary_key=True, default=generate_uuid)
    pin = Column(String(6), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    messages = relationship("Message", back_populates="room")
    
# databse model for Messages
class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=generate_uuid)
    text = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="messages")
    room = relationship("Room", back_populates="messages")
    
    __table_args__ = (
        Index("room_time_idx", "room_id", "created_at"), # Composite index for fetching room messages sorted by time
        Index("lobby_time_idx", "created_at",            # Partial index for created_at with filter where rooom_id is None
              postgresql_where=Column("room_id").is_(None)),
        Index("user_time_idx", "user_id", "created_at")  # Composite index for queries filtering by user_id and sorting by created_at
    )