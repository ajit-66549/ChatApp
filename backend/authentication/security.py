import bcrypt
import asyncio
from concurrent.futures import ThreadPoolExecutor

from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

executor = ThreadPoolExecutor(max_workers=3)

def _hash_password(password: str) -> str:
    """Add salt to the password, and then hash it"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def _verify_password(plain: str, hashed: str) -> bool:
    """Extract salt from the stored hash, add it to user password,
    hash it and compare with stored hash"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

async def hash_password(password: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _hash_password, password)

async def verify_password(plain: str, hashed: str) -> bool:
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, _verify_password, plain, hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)     # signed token
    return token

def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None