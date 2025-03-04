# app/services/llm_service.py
import asyncio
from app.core.sessions import chat_sessions
from vertexai.generative_models import GenerativeModel, ChatSession
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any

# Constants
MODEL_NAME = "gemini-2.0-flash-exp"  # "gemini-2.0-flash-thinking-exp-1219"
SESSION_EXPIRY_TIME = timedelta(hours=1)  # Expire sessions after 1 hour

async def chat_logic(request) -> AsyncGenerator[str, None]:  # Changed to AsyncGenerator
    """
    Handle LLM chat sessions asynchronously and stream the response.
    """
    session_id = request.session_id
    prompt = request.prompt

    try:
        if session_id in chat_sessions:
            session_data = chat_sessions[session_id]
            chat_session = session_data["chat_session"]
            if datetime.now() - session_data["last_used"] > SESSION_EXPIRY_TIME:
                chat_session = await start_new_chat_session(session_id)
        else:
            chat_session = await start_new_chat_session(session_id)

        chat_sessions[session_id]["last_used"] = datetime.now()

        # Send prompt to LLM and stream the response
        async def send_message_stream():  # Now an async function
            responses = chat_session.send_message(prompt, stream=True)
            for chunk in responses:  # Iterate directly over responses
                yield chunk.text  # Yield each chunk as it arrives

        async for chunk_text in send_message_stream():
            yield chunk_text

    except Exception as e:
        print(f"Error in chat_logic: {e}")
        yield f"Error: {e}" # Yield error message to avoid breaking the stream


async def start_new_chat_session(session_id):
    """
    Start a new chat session (made asynchronous).
    """
    try:
        # Initialize the LLM model *in a separate thread*
        def init_model_sync():
            model = GenerativeModel(MODEL_NAME)
            return model.start_chat()

        chat_session = await asyncio.to_thread(init_model_sync)

        # Store session in chat_sessions
        chat_sessions[session_id] = {
            "chat_session": chat_session,
            "last_used": datetime.now(),
        }
        return chat_session

    except Exception as e:
        # Log initialization error
        print(f"Error initializing chat session: {e}")
        raise RuntimeError("Failed to initialize chat session")



def cleanup_expired_sessions():
    """
    Clean up expired chat sessions.
    """
    try:
        current_time = datetime.now()
        expired_sessions = [
            session_id
            for session_id, session_data in chat_sessions.items()
            if current_time - session_data["last_used"] > SESSION_EXPIRY_TIME
        ]

        for session_id in expired_sessions:
            del chat_sessions[session_id]
            print(f"Session {session_id} expired and removed.")
    except Exception as e:
        print(f"Error cleaning up expired sessions: {e}")
