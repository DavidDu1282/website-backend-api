# app/services/counsellor_service.py
from app.models.llm import ChatRequest
from app.services.llm_service import chat_logic
from app.models.user import User
from app.models.counsellor_message_history import CounsellorMessageHistory
from app.data.database import get_db
from sqlalchemy.orm import Session
from app.core.dependencies import get_redis_client

import json
from fastapi import Depends
from redis.asyncio import Redis

async def analyse_counsellor_request(request, db: Session = Depends(get_db), redis_client: Redis = Depends(get_redis_client)):
    """
    Analyze user input, generate a response using the LLM, and manage caching.
    """
    # Validate user message
    if not hasattr(request, 'message') or not request.message.strip():
        raise ValueError("Invalid input: Message cannot be empty")

    # Determine language
    language = request.language if hasattr(request, 'language') else "en"

    # Get person identifier
    session_id = request.session_id if hasattr(request, 'session_id') else "default"

    # Define system messages for different languages
    system_messages = {
        "en": "You are a helpful and empathetic counsellor. Provide thoughtful and supportive advice.",
        "zh": "你是一个乐于助人且富有同情心的咨询师。请提供周到和支持性的建议。",
        "zh_TW": "你是一個樂於助人且富有同情心的諮詢師。請提供周到和支持性的建議："
    }

    async def build_counsellor_prompt(user_id, session_id, new_message, db: Session, redis_client: Redis):
        """Builds the prompt for the LLM, including message history."""
        user = db.query(User).get(user_id)

        base_prompt = system_messages.get(language, system_messages["en"])

        custom_prompt = user.custom_counsellor_prompt if user.custom_counsellor_prompt else ""

        # Generate a unique cache key
        cache_key = f"counsellor_history:{user_id}:{session_id}"

        # Try to get the message history from Redis
        cached_history = await redis_client.get(cache_key)

        if cached_history:
            message_history = json.loads(cached_history.decode('utf-8'))

        else:
            # If not in Redis, query the database
            message_history_objects = db.query(CounsellorMessageHistory).filter(
                CounsellorMessageHistory.user_id == user_id,
                CounsellorMessageHistory.session_id == session_id
            ).order_by(CounsellorMessageHistory.timestamp.desc()).limit(5).all()

            # Convert the SQLAlchemy objects to a list of dictionaries before caching
            message_history = [{"user_message": msg.user_message, "counsellor_response": msg.counsellor_response} for msg in message_history_objects]

            # Store the message history in Redis (as JSON)
            await redis_client.setex(cache_key, 3600, json.dumps(message_history))

        history_string = "\n".join([f"User: {msg['user_message']}\nCounsellor: {msg['counsellor_response']}" for msg in reversed(message_history)])

        final_prompt = f"{base_prompt}\n{custom_prompt}\n\nMessage History:\n{history_string}\n\nUser: {new_message}"

        return final_prompt

    # Build the prompt
    prompt = await build_counsellor_prompt(request.user_id, session_id, request.message, db, redis_client)

    # Prepare request for LLM
    llm_request = ChatRequest(session_id=request.session_id, prompt=prompt)

    try:
        response = chat_logic(llm_request)

        # Store the message and response in the database
        counsellor_message = CounsellorMessageHistory(
            user_id=request.user_id,
            session_id=session_id,
            user_message=request.message,
            counsellor_response=response["response"]
        )
        db.add(counsellor_message)
        db.commit()

        # Invalidate the cache (remove the old entry)
        cache_key = f"counsellor_history:{request.user_id}:{session_id}"
        await redis_client.delete(cache_key)

        return {
            "message": "Response generated successfully" if language == "en" else "回应生成成功",
            "response": response["response"]
        }
    except Exception as e:
        raise ValueError(f"Error during LLM processing: {e}" if language == "en" else f"LLM 处理时出错：{e}")