# app/services/bagua_services.py
import logging
from typing import AsyncGenerator
from fastapi import HTTPException
from app.models.llm_models import ChatRequest
from app.services.llm.llm_services import chat_logic
from sqlalchemy.orm import Session  # Keep this, it's good practice to pass db even if unused
from app.models.database_models.user import User # keep too

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def analyze_bagua_request(request: ChatRequest, db: Session, user: User) -> AsyncGenerator[str, None]:
    """
    Analyzes a Bagua request, generates an LLM response, and streams it.
    """
    logger.info("Starting Bagua service")
    logger.debug(f"Full Request: {request.__dict__}")

    # Validate request (adjust as needed for Bagua-specific validation)
    if not request.message or not request.message.strip():
        logger.warning("Invalid input: Message cannot be empty")
        raise HTTPException(status_code=400, detail="Message cannot be empty")


    language = request.language if request.language else "en"
    session_id = request.session_id or "default"

    # Language-specific prompt data
    language_prompts = {
        "en": {
            "question": "The user has asked the following question regarding their Bagua analysis:",
            "context": "User Context:",
            "analyze_direction": "Analyze the user's question and provide insights based on Bagua principles, considering the direction {direction}.",
            "analyze_general": "Analyze the user's question and provide a general Bagua analysis and insights.",
            "error_llm": "Error during LLM processing: ",
            "system_instruction": "You are a helpful Bagua and Feng Shui expert. Provide clear and insightful advice based on Bagua principles. Address the user's question directly. Answer in English."
        },
        "zh": {
            "question": "用户提出了以下关于八卦分析的问题：",
            "context": "用户背景：",
            "analyze_direction": "根据八卦原理分析用户的问题，并考虑{direction}方位，提供见解。",
            "analyze_general": "分析用户的问题，并提供一般的八卦分析和见解。",
            "error_llm": "LLM 处理时出错：",
            "system_instruction": "你是一位乐于助人的八卦和风水专家。根据八卦原理提供清晰且有见地的建议。直接回答用户的问题。用中文回答。"
        },
        "zh_TW": {
            "question": "使用者提出了以下關於八卦分析的問題：",
            "context": "使用者背景：",
            "analyze_direction": "根據八卦原理分析使用者的問題，並考慮{direction}方位，提供見解。",
            "analyze_general": "分析使用者的問題，並提供一般的八卦分析和見解。",
            "error_llm": "LLM 處理時出錯：",
            "system_instruction": "你是一位樂於助人的八卦和風水專家。根據八卦原理提供清晰且有見地的建議。直接回答使用者的問題。用繁體中文回答。"
        }
    }

    prompt_data = language_prompts.get(language, language_prompts["en"])
    system_instruction = prompt_data["system_instruction"]


    #  "Spread" concept adaptation for Bagua (Directional vs. General)
    if hasattr(request, 'direction') and request.direction:  # Check for a 'direction' attribute
        prompt = (
            f"{prompt_data['question']}\n"
            f"\"{request.message}\"\n\n"
            f"{prompt_data['context']}\n"
            f"\"{request.user_context if hasattr(request, 'user_context') and request.user_context else ''}\"\n\n"  # Handle optional user_context
            f"{prompt_data['analyze_direction'].format(direction=request.direction)}"
        )
    else:
        # General Bagua analysis (no specific direction)
        prompt = (
            f"{prompt_data['question']}\n"
            f"\"{request.message}\"\n\n"
             f"{prompt_data['context']}\n"
            f"\"{request.user_context if hasattr(request, 'user_context') and request.user_context else ''}\"\n\n"  # Handle optional user_context
            f"{prompt_data['analyze_general']}"
        )
    
    logger.info(prompt)
    llm_request = ChatRequest(session_id = session_id, prompt=prompt, language=language, system_instruction=system_instruction)


    response_chunks = []
    try:
        async for chunk in chat_logic(llm_request):
            response_chunks.append(chunk)
            yield chunk
    except Exception as e:
        logger.exception(f"Error during LLM processing: {e}")
        error_message = f"{prompt_data['error_llm']}{e}"
        yield error_message
        raise HTTPException(status_code=500, detail=error_message)
    logger.info("Received full response from LLM service.")