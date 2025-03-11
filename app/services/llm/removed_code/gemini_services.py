# app/services/llm/gemini_service.py
from datetime import datetime, timedelta
from typing import AsyncGenerator
from google import genai
from google.genai import types
from app.core.config import GEMINI_API_KEY
from app.models.llm_models import ChatRequest


# Configure the Gemini API Key globally (only once)
client = genai.Client(api_key=GEMINI_API_KEY)

# Gemini models with their rate limits (adjust as needed)
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

async def query_gemini_api(request: ChatRequest, model_name: str) -> AsyncGenerator[str, None]:
    """
    Queries Google Gemini API asynchronously while tracking rate limits.
    Handles streaming.  Correctly formats the prompt.
    """
    
    try:
        # Correctly format the prompt for Gemini
        formatted_prompt = [
            {"role": "user", "parts": [request.prompt]},  # Single turn, user prompt
        ]

        response = client.models.generate_content_stream(model=model_name, contents=formatted_prompt, system_instruction = request.system_instruction)

        # Update rate tracking (TPM, not TPD for a single request)
        GEMINI_MODELS[model_name]["used_rpm"] += 1
        GEMINI_MODELS[model_name]["used_tpm"] += sum(len(part) for part in request.prompt)  # Count tokens in prompt
        # No need to track TPD here; it's reset daily

        for chunk in response:
            GEMINI_MODELS[model_name]["used_tpm"] += len(chunk.text) # Add response tokens.
            yield chunk.text

    except Exception as e:
        print(f"Gemini API Error ({model_name}): {e}")
        yield f"Gemini API Error ({model_name}): {e}"


def get_available_gemini_model():
    """Returns the first available Gemini model (not exceeding limits)."""
    for model, limits in GEMINI_MODELS.items():
        if is_gemini_model_available(model):
            return model
    return None

def is_gemini_model_available(model: str) -> bool:
    """Checks if a Gemini model is under its rate limits."""
    limits = GEMINI_MODELS[model]
    return (
        limits["used_rpm"] < limits["rpm"]
        and limits["used_tpm"] < limits["tpm"]
        # TPD is checked on reset, not here
    )

def reset_gemini_rate_limits():
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
