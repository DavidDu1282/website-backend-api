# d:\OtherCodingProjects\website-backend-api\app\data\database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

if "sqlite" in settings.DATABASE_URL.lower():
    raise ValueError("SQLite does not support async operations.  Use PostgreSQL with asyncpg.")

async_database_url = settings.DATABASE_URL
if not async_database_url.startswith("postgresql+asyncpg://"):
    async_database_url = async_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(f"Warning: Adapted database URL to: {async_database_url}.  Please update your configuration.")


engine = create_async_engine(async_database_url)#, echo=settings.DEBUG)

AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()