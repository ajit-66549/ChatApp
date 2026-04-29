from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import joinedload
from models import Message

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