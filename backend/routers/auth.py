from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from repositories import UserRepository
from auth import hash_password, verify_password, create_access_token
from schemas import SignupRequest, SignupResponse, LoginRequest, LoginResponse
from dependencies import get_current_user
from models import User

router = APIRouter(prefix="/auth")


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    user_repo = UserRepository(db)
    if await user_repo.exists(body.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    hashed = await hash_password(body.password)
    user = await user_repo.create(username=body.username, hashed_password=hashed)
    return user


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_username(body.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    is_valid = await verify_password(body.password, user.password)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.id, "username": user.username})
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username
    )


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at
    }