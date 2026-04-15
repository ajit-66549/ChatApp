import bcrypt
import asyncio
from concurrent.futures import ThreadPoolExecutor

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