import asyncio
from typing import AsyncGenerator, Optional
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from app.models.llm_models import ChatRequest
from app.core.sessions import chat_sessions
from app.core.startup import llm_clients
from google.api_core.exceptions import ResourceExhausted, InternalServerError, ServiceUnavailable, GoogleAPIError
from app.models.llm_models import ChatRequest

GEMINI_MODELS = {
    # Vertex AI Models
    "gemini-2.0-flash-exp": {"rpm": 10, "type": "vertex"},
    # "gemini-2.5-pro-exp-03-25": {"rpm": 10, "type": "vertex"},
    # Gemini API Models
    "gemini-2.5-pro-exp-03-25": {"rpm": 2, "type": "gemini"},
    "gemini-1.5-pro-latest": {"rpm": 2, "type": "gemini"},
    "gemini-1.5-flash-latest": {"rpm": 15, "type": "gemini"},
    "gemini-1.5-flash-8b-latest": {"rpm": 15, "type": "gemini"},
    "gemini-2.0-flash": {"rpm": 15, "type": "gemini"},
    "gemini-2.0-flash-lite": {"rpm": 30, "type": "gemini"},
    "gemini-2.0-pro-exp": {"rpm": 2, "type": "gemini"},
    "gemini-2.5-pro-exp-03-25": {"rpm": 2, "type": "gemini"},
}

SESSION_EXPIRY_TIME = timedelta(hours=1)

last_request_times = {}
request_counts = {}

async def query_genai_api(chat_session, request: ChatRequest, model_name: str, model_config) -> AsyncGenerator[str, None]:
    """
    Queries the Gemini API (or Vertex AI), handling rate limiting.

    Args:
        chat_session: The active chat session object.
        request: The ChatRequest object.
        model_name: The name of the model being used.
        model_config: The configuration dictionary for the model.
    """
    now = datetime.now()
    if model_name in last_request_times:
        time_since_last_request = (now - last_request_times[model_name]).total_seconds()
        if time_since_last_request < 60:
            if request_counts[model_name] >= model_config["rpm"]:
                yield "Rate limit exceeded. Please wait and try again."
                return
        else:
            request_counts[model_name] = 0

    if model_name not in request_counts:
        request_counts[model_name] = 0
    if model_name not in last_request_times:
        last_request_times[model_name] = now

    try:
        request_counts[model_name] += 1
        last_request_times[model_name] = now

        responses = chat_session.send_message_stream(request.prompt, config=types.GenerateContentConfig(system_instruction=request.system_instruction))

        for chunk in responses:
            await asyncio.sleep(0)
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


async def _llm_query_helper(prompt: str, model: Optional[str] = None) -> str:
    """Helper function to query LLMs, reusing chat_logic's model selection."""

    request = ChatRequest(session_id="dummy_session", prompt=prompt, model=model)
    response_generator = query_genai_api(request=request, model_name=model or list(GEMINI_MODELS.keys())[0], user_id="dummy_user_id")  # Default to the first model if none specified

    full_response = ""
    async for chunk in response_generator:
        full_response += chunk

    return full_response