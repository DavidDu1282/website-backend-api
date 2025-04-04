# app/core/startup.py
from datetime import datetime  # Corrected import

from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter

from google import genai
from redis.asyncio import Redis

from app.core.config import GEMINI_API_KEY, settings
from app.core.dependencies import get_redis_client
from app.core.sessions import chat_sessions
from app.data.tarot import load_tarot_data

redis_client_instance: Redis = None
llm_clients = {}

async def startup_event(app: FastAPI):
    """
    Initialize resources on application startup.
    """
    global redis_client_instance
    global llm_clients
    global chat_sessions

    try:
        load_tarot_data("app/data/optimized_tarot_translated.json")
        print("Tarot data loaded successfully.")

        llm_clients["gemini"] = genai.Client(api_key=GEMINI_API_KEY)
        llm_clients["vertex"] = genai.Client(vertexai=True, project=settings.GOOGLE_PROJECT_ID, location=settings.GOOGLE_REGION)

        chat_sessions["dummy_session"] = {
            "chat_session": llm_clients["gemini"].chats.create(model="gemini-2.0-flash-lite"),
            "last_used": datetime.now(),
            "user_id": "dummy_user_id"
        }
        async for client in get_redis_client():
            redis_client_instance = client
            break 

        await FastAPILimiter.init(redis_client_instance, prefix="limit:")
        print("FastAPILimiter initialized successfully.")

    except Exception as e:
        print(f"Failed to startup: {e}")
        raise
