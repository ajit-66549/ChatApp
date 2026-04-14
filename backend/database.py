from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv()

#build databse url
DB_URL = (
    f"postgresql+asyncpg://"
    f"{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}"
    f"@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}"
    f"/{os.getenv("DB_NAME")}"
)

#create an engine that connects to the database
engine = create_async_engine(
    DB_URL,
    pool_size=10,
    max_overflow=20,
    echo=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()