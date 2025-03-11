# app/services/llm/vertex_service.py
from datetime import datetime, timedelta
from typing import AsyncGenerator
from app.core.sessions import chat_sessions  # Import chat_sessions
from app.models.llm_models import ChatRequest
from google import genai
from google.genai import types
from app.core.config import settings

# Constants
VERTEX_MODEL_NAME = "gemini-2.0-flash-exp"
SESSION_EXPIRY_TIME = timedelta(hours=1)
client = genai.Client(vertexai=True,
                    project=settings.GOOGLE_PROJECT_ID,
                location=settings.GOOGLE_REGION)

async def query_vertex_ai_api(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Queries Vertex AI's Gemini model asynchronously, managing sessions.
    """
    try:
        if request.session_id in chat_sessions:
            session_data = chat_sessions[request.session_id]
            chat = session_data["chat"]
            if datetime.now() - session_data["last_used"] > SESSION_EXPIRY_TIME:
                await close_vertex_session(request.session_id)  # Close the old session
                chat = await start_new_vertex_chat_session(request.session_id)  # Start new session
        else:
            chat = await start_new_vertex_chat_session(request.session_id)

        chat_sessions[request.session_id]["last_used"] = datetime.now()
        responses = chat.send_message_stream(request.prompt, config=types.GenerateContentConfig(system_instruction=request.system_instruction))
        
        for chunk in responses:
            yield chunk.text

    except Exception as e:
        print(f"Vertex AI Error: {e}")
        yield f"Vertex AI Error: {e}"


async def start_new_vertex_chat_session(session_id):
    """Starts a new Vertex AI chat session."""
    try:
        chat = client.chats.create(model="gemini-2.0-flash")
        chat_sessions[session_id] = {
            "chat": chat,
            "last_used": datetime.now(),
        }
        return chat
    except Exception as e:
        print(f"Error starting Vertex AI session: {e}")
        raise 


async def close_vertex_session(session_id):
    """Closes a Vertex AI chat session, handling potential errors."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]


def cleanup_expired_vertex_sessions():
    """Removes expired Vertex AI chat sessions."""
    global chat_sessions
    now = datetime.now()
    expired_sessions = [
        session_id
        for session_id, session_data in chat_sessions.items()
        if now - session_data["last_used"] > SESSION_EXPIRY_TIME
    ]

    for session_id in expired_sessions:
        # Vertex AI sessions don't need explicit closing
        del chat_sessions[session_id]
    if expired_sessions:
        print(f"Cleaned up {len(expired_sessions)} expired chat sessions.")