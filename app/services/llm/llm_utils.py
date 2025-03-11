# app/services/llm/llm_utils.py
from datetime import datetime, timedelta
from typing import AsyncGenerator
from google import genai
from google.genai import types
from app.models.llm_models import ChatRequest
from app.core.sessions import chat_sessions
from app.core.startup import llm_clients
from google.api_core.exceptions import ResourceExhausted, InternalServerError, ServiceUnavailable, GoogleAPIError  # Import exceptions

# --- Configuration ---

# Define available models and their configurations (combine both)
GEMINI_MODELS = {
    # Vertex AI Models (using Vertex AI project/location)
    "gemini-2.0-flash-exp": {"rpm": 10, "type": "vertex"},  # Example Vertex AI model
    # Gemini API Models (using API Key)
    "gemini-1.5-pro-latest": {"rpm": 2, "type": "gemini"},
    "gemini-1.5-flash-latest": {"rpm": 15, "type": "gemini"},
    "gemini-1.5-flash-8b-latest": {"rpm": 15, "type": "gemini"},
    "gemini-2.0-flash": {"rpm": 15, "type": "gemini"},
    "gemini-2.0-flash-lite": {"rpm": 30, "type": "gemini"},
    "gemini-2.0-pro-exp": {"rpm": 2, "type": "gemini"},
}

SESSION_EXPIRY_TIME = timedelta(hours=1)

# --- Client Initialization ---
# We'll initialize clients as needed, based on the request type

# --- Rate Limiting (Simplified, Per-Model) ---
last_request_times = {}  # Track last request time *per model*
request_counts = {}  # Track request count *per model*

# --- Main Query Function ---

async def query_genai_api(request: ChatRequest, model_name: str) -> AsyncGenerator[str, None]:
    """
    Queries either the Gemini API or Vertex AI, handling sessions and rate limiting.

    Args:
        request: The ChatRequest object.
        model_name: The name of the model to use (must be in GEMINI_MODELS).
    """
    if model_name not in GEMINI_MODELS:
        yield f"Error: Model '{model_name}' not found."
        return

    model_config = GEMINI_MODELS[model_name]
    model_type = model_config["type"]

    # --- Rate Limiting Check (Simplified) ---
    now = datetime.now()
    if model_name in last_request_times:
        time_since_last_request = (now - last_request_times[model_name]).total_seconds()
        if time_since_last_request < 60:
            if request_counts[model_name] >= model_config["rpm"]:
                yield "Rate limit exceeded. Please wait and try again."
                return
        else:
            request_counts[model_name] = 0  # Reset count

    # Initialize if this is the first request for this model
    if model_name not in request_counts:
        request_counts[model_name] = 0
    if model_name not in last_request_times:
        last_request_times[model_name] = now


    try:
        # --- Session Management ---
        if request.session_id in chat_sessions:
            session_data = chat_sessions[request.session_id]
            chat_session = session_data["chat_session"]
            if datetime.now() - session_data["last_used"] > SESSION_EXPIRY_TIME:
                await close_session(request.session_id)
                chat_session = await start_new_chat_session(request.session_id, model_name, llm_clients[model_type])
        else:
            chat_session = await start_new_chat_session(request.session_id, model_name, llm_clients[model_type])

        chat_sessions[request.session_id]["last_used"] = datetime.now()

        # --- API Call ---
        request_counts[model_name] += 1  # Increment *before* API call
        last_request_times[model_name] = now

        responses = chat_session.send_message_stream(request.prompt, config=types.GenerateContentConfig(system_instruction=request.system_instruction))

        for chunk in responses:
            yield chunk.text

    except ResourceExhausted:
        yield "Rate limit exceeded by underlying API. Please wait and try again."
    except (InternalServerError, ServiceUnavailable):
        yield "The LLM service is temporarily unavailable.  Please try again later."
    except GoogleAPIError as e:
        print(f"Google API Error: {e}")
        yield f"Google API Error: {e}"
    except Exception as e:
        print(f"Unexpected Error: {e}")
        yield f"An unexpected error occurred: {e}"

# --- Session Management Functions ---

async def start_new_chat_session(session_id: str, model_name:str, client: genai.Client):
    """Starts a new chat session."""
    try:
        chat_session = client.chats.create(model=model_name)
        # model = client.get_model(model_name)  # Use get_model for both
        # chat_session = model.start_chat()
        chat_sessions[session_id] = {
            "chat_session": chat_session,
            "last_used": datetime.now(),
        }
        return chat_session
    except Exception as e:
        print(f"Error starting session: {e}")
        raise

async def close_session(session_id: str):
    """Closes a chat session."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]

def cleanup_expired_sessions():
    """Removes expired chat sessions."""
    global chat_sessions
    now = datetime.now()
    expired_sessions = [
        session_id
        for session_id, session_data in chat_sessions.items()
        if now - session_data["last_used"] > SESSION_EXPIRY_TIME
    ]
    for session_id in expired_sessions:
        del chat_sessions[session_id]
    if expired_sessions:
        print(f"Cleaned up {len(expired_sessions)} expired sessions.")