# app/services/llm_service.py
import asyncio
from google import genai  # Use the generativeai alias
from app.core.sessions import chat_sessions
from app.core.config import GEMINI_API_KEY
from vertexai.generative_models import GenerativeModel, ChatSession
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional, Dict, Union
import random
import os

# Constants
VERTEX_MODEL_NAME = "gemini-2.0-flash-exp"  # Or your preferred Vertex AI model
SESSION_EXPIRY_TIME = timedelta(hours=1)

# Gemini models with their rate limits (adjust as needed)
#  Requests per minute (RPM)
#  Tokens per minute (TPM)
#  Tokens per day (TPD)
GEMINI_MODELS = {
    "gemini-1.5-pro-latest": {"rpm": 2, "tpm": 32_000, "rpd": 50, "used_rpm": 0, "used_tpm": 0, "used_rpd": 0},
    "gemini-1.5-flash-latest": {"rpm": 15, "tpm": 1_000_000, "rpd": 1500, "used_rpm": 0, "used_tpm": 0, "used_rpd": 0},
    "gemini-1.5-flash-8b-latest": {"rpm": 15, "tpm": 1_000_000, "rpd": 1500, "used_rpm": 0, "used_tpm": 0, "used_rpd": 0},
    "gemini-2.0-flash": {"rpm": 15, "tpm": 1_000_000, "rpd": 1500, "used_rpm": 0, "used_tpm": 0, "used_rpd": 0},
    "gemini-2.0-flash-lite": {"rpm": 30, "tpm": 1_000_000, "rpd": 1500, "used_rpm": 0, "used_tpm": 0, "used_rpd": 0},
    "gemini-2.0-pro-exp": {"rpm": 2, "tpm": 1_000_000, "rpd": 50, "used_rpm": 0, "used_tpm": 0, "used_rpd": 0},
    # "learnlm-1.5-pro-experimental": {"rpm": None, "tpm": 32_767, "rpd": None, "used_rpm": 0, "used_tpm": 0, "used_rpd": 0}
}

# Track last reset times
last_minute_reset = datetime.now()
last_day_reset = datetime.now()

# Configure the Gemini API Key globally (only once) - Important for efficiency
client = genai.Client(api_key=GEMINI_API_KEY)

# # List available models
# models = client.models.list()

# # Print available models
# for model in models:
#     print(model)

async def chat_logic(request) -> AsyncGenerator[str, None]:
    """
    Handles LLM chat sessions, allowing the use of both Vertex AI and Gemini APIs.
    Prioritizes based on user selection, then availability.
    """
    session_id = request.session_id
    prompt = request.prompt
    user_selected_model = request.model

    reset_rate_limits()

    # --- Model Selection Logic ---
    if user_selected_model:
        if user_selected_model == "vertex-ai":
            try:
                async for chunk in query_vertex_ai_api(session_id, prompt):
                    yield chunk
                return
            except Exception as e:
                yield f"Vertex AI Error: {e}.  Falling back to Gemini."

        elif user_selected_model in GEMINI_MODELS:
            if is_model_available(user_selected_model):
                async for chunk in query_gemini_api(prompt, user_selected_model):
                    yield chunk
                return
            else:
                yield f"Error: Model '{user_selected_model}' has exceeded its rate limit.  Trying other models..."

        else:  # Invalid model selection
            yield f"Error: Invalid model selected: {user_selected_model}. Trying other models..."

    # --- Fallback Logic (if no user selection or selected model fails) ---

    # Try Vertex AI first (if no specific model was requested)
    if not user_selected_model or (user_selected_model == "vertex-ai"):
        try:
            async for chunk in query_vertex_ai_api(session_id, prompt):
                yield chunk
            return  # success
        except Exception as e:
            print(f"Vertex AI failed: {e}")  # Log the specific error

    # Try Gemini models (prioritize those not exceeding limits)
    available_gemini_model = get_available_gemini_model()
    if available_gemini_model:
        async for chunk in query_gemini_api(prompt, available_gemini_model):
            yield chunk
        return  # success

    # --- All models failed ---
    yield "Error: All models are unavailable or have exceeded their rate limits. Try again later."

async def query_gemini_api(prompt: str, model_name: str) -> AsyncGenerator[str, None]:
    """
    Queries Google Gemini API asynchronously while tracking rate limits.
    Handles streaming.  Correctly formats the prompt.
    """
    try:
        # Correctly format the prompt for Gemini
        formatted_prompt = [
            {"role": "user", "parts": [prompt]},  # Single turn, user prompt
        ]

        response = client.models.generate_content_stream(model=model_name, contents=prompt)

        # Update rate tracking (TPM, not TPD for a single request)
        GEMINI_MODELS[model_name]["used_rpm"] += 1
        GEMINI_MODELS[model_name]["used_tpm"] += sum(len(part) for part in prompt)  # Count tokens in prompt
        # No need to track TPD here; it's reset daily

        for chunk in response:
            GEMINI_MODELS[model_name]["used_tpm"] += len(chunk.text) # Add response tokens.
            yield chunk.text

    except Exception as e:
        print(f"Gemini API Error ({model_name}): {e}")
        yield f"Gemini API Error ({model_name}): {e}"

async def query_vertex_ai_api(session_id, prompt) -> AsyncGenerator[str, None]:
    """
    Queries Vertex AI's Gemini model asynchronously, managing sessions.
    """
    try:
        if session_id in chat_sessions:
            session_data = chat_sessions[session_id]
            chat_session = session_data["chat_session"]
            if datetime.now() - session_data["last_used"] > SESSION_EXPIRY_TIME:
                await close_vertex_session(session_id)  # Close the old session
                chat_session = await start_new_chat_session(session_id)  # Start new session
        else:
            chat_session = await start_new_chat_session(session_id)

        chat_sessions[session_id]["last_used"] = datetime.now()

        responses = await chat_session.send_message_async(prompt, stream=True)  # Await send_message_async
        async for chunk in responses:  # Use async for
            yield chunk.text

    except Exception as e:
        print(f"Vertex AI Error: {e}")
        # Don't raise here, let the caller handle fallback.  Just yield the error.
        yield f"Vertex AI Error: {e}"

async def start_new_chat_session(session_id):
    """Starts a new Vertex AI chat session."""
    try:
        model = GenerativeModel(VERTEX_MODEL_NAME)
        chat = model.start_chat()  # No need for to_thread
        chat_sessions[session_id] = {
            "chat_session": chat,
            "last_used": datetime.now(),
        }
        return chat
    except Exception as e:
        print(f"Error starting Vertex AI session: {e}")
        raise  # Re-raise for startup/initialization errors

async def close_vertex_session(session_id):
    """Closes a Vertex AI chat session, handling potential errors."""
    if session_id in chat_sessions:
        try:
            # Vertex AI ChatSession objects *do not* have an explicit close/end method.
            # Just deleting the session from the dictionary is sufficient.
            pass  # No explicit close needed
        except Exception as e:
            print(f"Error closing Vertex AI session {session_id}: {e}")
        finally:
            del chat_sessions[session_id]

def get_available_gemini_model() -> Optional[str]:
    """Returns the first available Gemini model (not exceeding limits)."""
    for model, limits in GEMINI_MODELS.items():
        if is_model_available(model):
            return model
    return None

def is_model_available(model: str) -> bool:
    """Checks if a Gemini model is under its rate limits."""
    limits = GEMINI_MODELS[model]
    return (
        limits["used_rpm"] < limits["rpm"]
        and limits["used_tpm"] < limits["tpm"]
        # TPD is checked on reset, not here
    )

def reset_rate_limits():
    """Resets per-minute and per-day rate limits."""
    global last_minute_reset, last_day_reset
    now = datetime.now()

    if (now - last_minute_reset).total_seconds() >= 60:
        for model_data in GEMINI_MODELS.values():
            model_data["used_rpm"] = 0
            model_data["used_tpm"] = 0 # reset tpm per minute
        last_minute_reset = now

    if (now - last_day_reset).total_seconds() >= 86400:
        for model_data in GEMINI_MODELS.values():
            model_data["used_tpd"] = 0
        last_day_reset = now

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
        # Vertex AI sessions don't need explicit closing
        del chat_sessions[session_id]
    if expired_sessions:
        print(f"Cleaned up {len(expired_sessions)} expired chat sessions.")

# # New potential function to generate reflection and plan based on relavant chat history
# import httpx

# async def generate_summary(conversation_history: str) -> str:
#     prompt = f"""Summarize the following conversation...

#     Conversation History:
#     {conversation_history}

#     Summary:"""

#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             "YOUR_LLM_API_ENDPOINT",
#             json={"prompt": prompt, "max_tokens": 200},  # Adjust parameters as needed
#             headers={"Authorization": "Bearer YOUR_API_KEY"},
#         )
#     response.raise_for_status()  # Raise an exception for bad status codes
#     return response.json()["choices"][0]["text"]

# async def generate_reflection(summary: str, user_id: int) -> str:
#   # Similar structure to generate_summary, but with a different prompt
#   prompt = f"""Based on the following summary of a user's interactions with an AI counsellor, generate a thoughtful reflection...
#       Summary: {summary}
#       User ID: {user_id}
#       Reflection:
#       """
#   async with httpx.AsyncClient() as client:
#       response = await client.post(
#           "YOUR_LLM_API_ENDPOINT",
#           json={"prompt": prompt, "max_tokens": 300},
#           headers={"Authorization": "Bearer YOUR_API_KEY"},
#       )
#       response.raise_for_status()
#       return response.json()["choices"][0]["text"]

# async def generate_plan(reflection: str, summary: str) -> str:
#     prompt = f"""Based on the following reflection and summary, create a plan for the AI counsellor's next conversation with the user.

#         Reflection: {reflection}
#         Summary: {summary}

#         Plan for Next Conversation:
#         - Topics to Explore:
#         - Questions to Ask:
#         - Techniques to Consider:
#         - Goals for the session:"""

#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             "YOUR_LLM_API_ENDPOINT",
#             json={"prompt": prompt, "max_tokens": 400},
#             headers={"Authorization": "Bearer YOUR_API_KEY"},
#         )
#         response.raise_for_status()
#         return response.json()["choices"][0]["text"]