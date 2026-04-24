from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from repositories import UserRepository
from auth import decode_access_token
from models import User

async def get_current_user(authorization: str = Header(...), db: AsyncSession = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format. Use: Bearer <token>")
    
    token = authorization.split(" ")[1]    # take token from the authorization header
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")          # extract user_id from the payload
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
async def get_optional_user(authorization: str = Header(...), db: AsyncSession = Depends(get_db)) -> User|None:
    if not authorization:
        return None
    
    try:
        await get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None