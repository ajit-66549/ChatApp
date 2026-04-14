from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Room

class RoomRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get_by_pin(self, pin: str) -> Room | None:
        result = await self.db.execute(
            select(Room).where(Room.pin == pin)
            )
        return result.scalar_one_or_none()
    
    async def get_by_id(self, id: str) -> Room | None:
        result = await self.db.execute(
            select(Room).where(Room.id == id)
        )
        return result.scalar_one_or_none()
    
    async def exists(self, pin: str) -> bool:
        room = self.get_by_pin(pin)
        return room is not None
    
    async def create(self, pin: str) -> Room:
        room = Room(pin=pin)
        self.db.add(room)
        try:
            await self.db.commit()
            await self.db.refresh(room)
            return room
        except Exception as e:
            await self.db.rollback()
            raise e
    
    async def delete_room(self, pin: str):
        room = await self.get_by_pin(pin)
        if room:
            await self.db.delete(room)
            await self.db.commit()