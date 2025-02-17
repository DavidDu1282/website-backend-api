from fastapi import FastAPI
from app.data.tarot import load_tarot_data
from app.services.llm_service import cleanup_expired_sessions
from fastapi_limiter import FastAPILimiter
import vertexai
import redis.asyncio as redis  # Use asyncio Redis client
from app.core.config import settings  # Import settings


async def startup_event():
    """
    Initialize resources on application startup.
    """
    try:
        load_tarot_data("app/data/optimized_tarot_translated.json")
        print("Tarot data loaded successfully.")
        cleanup_expired_sessions()
        
        # 🔹 Initialize Vertex AI here (once at startup)
        vertexai.init(
            project=settings.GOOGLE_PROJECT_ID,
            location=settings.GOOGLE_REGION
        )
        print(f"Vertex AI initialized for project: {settings.GOOGLE_PROJECT_ID} in {settings.GOOGLE_REGION}")

        # 🔹 Use Redis URL from config settings
        redis_connection = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

        # Initialize FastAPI rate limiter with Redis
        await FastAPILimiter.init(redis_connection)
        print(f"FastAPILimiter initialized with Redis at {settings.REDIS_URL}")

    except Exception as e:
        print(f"Failed to startup: {e}")
        raise
