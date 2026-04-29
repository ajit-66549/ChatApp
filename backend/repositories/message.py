from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import joinedload
from models import Message

import time

class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def save_message(self, text: str, user_id: str, room_id: str | None = None) -> Message:
        message = Message(text=text, user_id=user_id, room_id=room_id)
        self.db.add(message)
        try:
            await self.db.commit()
            await self.db.refresh(message)
            return message
        except Exception as e:
            await self.db.rollback()
            raise e
    
    async def save_message_with_timings(self, text: str, user_id: str, room_id: str | None = None) -> tuple[Message, dict[str, float]]:
        start = time.perf_counter()
        message = Message(text=text, user_id=user_id, room_id=room_id)
        self.db.add(message)
        add_done = time.perf_counter()
        try:
            commit_start = time.perf_counter()
            await self.db.commit()
            commit_done = time.perf_counter()
            
            refresh_start = time.perf_counter()
            await self.db.refresh(message)
            refresh_done = time.perf_counter()
            
            timings_ms = {
                "model_init_ms": (add_done - start) * 1000,
                "commit_ms": (commit_done - commit_start) * 1000,
                "refresh_ms": (refresh_done - refresh_start) * 1000,
                "repo_total_ms": (refresh_done - start) * 1000,
            }
            
            return message, timings_ms
        except Exception as e:
            await self.db.rollback()
            raise e
    
    async def get_lobby_messages(self, limit: int = 50, offset: int = 0) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .options(joinedload(Message.user))
            .where(Message.room_id.is_(None))
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def get_room_messages(self, room_id: str, limit: int = 50, offset: int = 0) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .options(joinedload(Message.user))
            .where(Message.room_id == room_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def count_lobby_messages(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Message).where(Message.room_id.is_(None))
        )
        return result.scalar_one()
    
    async def count_room_messages(self, room_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Message).where(Message.room_id == room_id)
        )
        return result.scalar_one()
    
    async def explain_lobby(self) -> list[str]:
        result = await self.db.execute(text("""
                                       EXPLAIN ANALYZE 
                                       SELECT * FROM messages 
                                       WHERE room_id is Null 
                                       ORDER BY created_at desc
                                       LIMIT 50
                                       """))
        return [row[0] for row in result.fetchall()]

    async def explain_room(self, room_id: str) -> list[str]:
        result = await self.db.execute(text(f"""
                                            EXPLAIN ANALYZE
                                            SELECT * FROM messages
                                            WHERE room_id = '{room_id}'
                                            ORDER BY created_at DESC
                                            LIMIT 50
                                        """))
        return [row[0] for row in result.fetchall()]