# app/core/startup.py
from fastapi import FastAPI
from app.data.tarot import load_tarot_data
from app.services.llm_service import cleanup_expired_sessions
from fastapi_limiter import FastAPILimiter
import vertexai
from app.core.config import settings
from app.core.dependencies import get_redis_client
from redis.asyncio import Redis  # Import Redis type

# Define a global variable to hold the Redis client instance
redis_client_instance: Redis = None

async def startup_event(app: FastAPI):
    """
    Initialize resources on application startup.
    """
    global redis_client_instance  # Use the global variable

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

        # Get the Redis client from the dependency
        # Use next(get_redis_client()) to get the value from the generator
        async for client in get_redis_client():
            redis_client_instance = client
            break  # Ensure you only get one client instance

        # Initialize FastAPILimiter with the global redis client
        await FastAPILimiter.init(redis_client_instance, prefix="limit:")
        print("FastAPILimiter initialized successfully.")


    except Exception as e:
        print(f"Failed to startup: {e}")
        raise
