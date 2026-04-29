from sqlalchemy.ext.asyncio import AsyncSession
from authentication.security import decode_access_token
from repositories import UserRepository
from models import User

async def authenticate_websocket_user(token: str, db: AsyncSession) -> User|None:
    payload = decode_access_token(token)
    if not payload:
        return None
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(payload.get("sub"))
    if not user or not user.is_active:
        return None
    
    return user