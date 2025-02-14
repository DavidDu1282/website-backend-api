from fastapi import FastAPI
from app.data.tarot import load_tarot_data
from app.services.llm_service import cleanup_expired_sessions
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis  # Use asyncio Redis client


async def startup_event():
    """
    Initialize resources on application startup.
    """
    try:
        load_tarot_data("app/data/optimized_tarot_translated.json")
        print("Tarot data loaded successfully.")
        cleanup_expired_sessions()

        # Create a Redis connection pool
        redis_connection = redis.from_url("redis://localhost:6379", encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_connection) # Use Redis connection
        print("FastAPILimiter initialized with Redis.")

    except Exception as e:
        print(f"Failed to startup: {e}")
        raise
