from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, username: str, hashed_password: str) -> User:
        user = User(username=username, password=hashed_password) # make python object
        self.db.add(user)            # stage data
        try: 
            await self.db.commit()       # write to the db
            await self.db.refresh(user)  # re-fetch the user
            return user
        except Exception as e:
            await self.db.rollback()
            raise e

    async def exists(self, username: str) -> bool:
        user = await self.get_by_username(username=username)
        return user is not None

    async def delete_by_id(self, id: str) -> bool:
        user = await self.get_by_id(id)
        if not user:
            return False
        await self.db.delete(user)
        try:
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete_by_username(self, username: str) -> bool:
        user = await self.get_by_username(username)
        if not user:
            return False
        await self.db.delete(user)
        try:
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            raise e   