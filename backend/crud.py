from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Room, Message

async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, username: str, hashed_password: str) -> User:
    user = User(username=username, password=hashed_password) # make python object
    db.add(user)            # stage data
    await db.commit()       # write to the db
    await db.refresh(user)  # re-fetch the user
    return user 

async def get_room_by_pin(db: AsyncSession, pin: str) -> Room | None:
    result = await db.execute(
        select(Room).where(Room.pin == pin)
    )
    return result.scalar_one_or_none()

async def create_room(db: AsyncSession, pin: str) -> Room:
    room = Room(pin=pin)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room

async def delete_room(db: AsyncSession, pin: str):
    room = await get_room_by_pin(db, pin)
    if room:
        await db.delete(room)
        await db.commit()
    
async def save_message(db: AsyncSession, text: str, user_id: str, room_id: str | None = None) -> Message:
    message = Message(text=text, user_id=user_id, room_id=room_id)
    db.add(message)
    try:
        await db.commit()
        await db.refresh(message)
        return message
    except Exception as e:
        await db.rollback()
        raise e
    
async def get_lobby_messages(db: AsyncSession, limit: int = 50) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.room_id.is_(None))
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()

async def get_room_messages(db: AsyncSession, room_id: str, limit: int = 50) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()