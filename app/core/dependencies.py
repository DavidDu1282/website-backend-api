# app/core/dependencies.py
import redis.asyncio as redis  # Use asyncio Redis client
from app.core.config import settings

async def get_redis_client():
    """Dependency to provide a Redis client."""
    redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        yield redis_client
    finally:
        await redis_client.close()  # Close the connection when done