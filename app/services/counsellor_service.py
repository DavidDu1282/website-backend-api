# app/services/counsellor_service.py
import json
import logging
from typing import List, AsyncGenerator

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.models.llm import ChatRequest  # Changed to correct import
from app.models.database_models.counsellor_message_history import CounsellorMessageHistory
from app.models.database_models.user import User
from app.models.database_models.user_prompt import UserPrompt
from app.services.llm_service import chat_logic  # Import your LLM service

# Configure logging (adjust level and format as needed)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def analyse_counsellor_request(request: ChatRequest, db: Session, redis_client: Redis, user: User) -> AsyncGenerator[str, None]:
    """
    Analyzes user input, generates an LLM response, and manages caching.
    Streams the response back to the client.
    """
    logging.debug("Starting analyse_counsellor_request")

    # Validate user message (more robust check)
    if not request.message or not request.message.strip():
        logging.warning("Invalid input: Message cannot be empty")
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    language = request.language if request.language else "en"
    session_id = request.session_id if request.session_id else "default"

    # Define system messages (clearer structure)
    system_messages = {
        "en": "You are a helpful and empathetic counsellor. Provide thoughtful and supportive advice.",
        "zh": "你是一个乐于助人且富有同情心的咨询师。请提供周到和支持性的建议。",
        "zh_TW": "你是一個樂於助人且富有同情心的諮詢師。請提供周到和支持性的建議：",
    }
    base_prompt = system_messages.get(language, system_messages["en"])

    async def build_counsellor_prompt(user: User, session_id: str, new_message: str, db: Session, redis_client: Redis) -> str:
        """Builds the complete prompt for the counsellor."""
        try:
            logging.debug(f"Building counsellor prompt for user: {user.username}, session: {session_id}")

            # --- Get Custom Prompt ---
            custom_prompt_obj = db.query(UserPrompt).filter(
                UserPrompt.user_id == user.id,
                UserPrompt.prompt_type == "counsellor"
            ).order_by(UserPrompt.timestamp.desc()).first()

            custom_prompt = custom_prompt_obj.prompt_text if custom_prompt_obj else ""

            # --- Get Message History ---
            cache_key = f"counsellor_history:{user.id}:{session_id}"
            cached_history = await redis_client.get(cache_key)
            if cached_history:
                if isinstance(cached_history, bytes):
                    message_history = json.loads(cached_history.decode('utf-8'))
                else:
                    message_history = json.loads(cached_history)
                logging.debug("Message history retrieved from Redis.")
            else:
                message_history_objects: List[CounsellorMessageHistory] = db.query(CounsellorMessageHistory).filter(
                    CounsellorMessageHistory.user_id == user.id,
                    CounsellorMessageHistory.session_id == session_id
                ).order_by(CounsellorMessageHistory.timestamp.desc()).limit(5).all()

                message_history = [
                    {"user_message": msg.user_message, "counsellor_response": msg.counsellor_response}
                    for msg in message_history_objects
                ]
                await redis_client.setex(cache_key, 3600, json.dumps(message_history))
                logging.debug(f"Message history stored in Redis: {cache_key}")

            # --- Format History ---
            history_string = "\n".join(
                [f"User: {msg['user_message']}\nCounsellor: {msg['counsellor_response']}"
                 for msg in reversed(message_history)]
            )

            # --- Combine Everything ---
            final_prompt = f"{base_prompt}\n{custom_prompt}\n\nMessage History:\n{history_string}\n\nUser: {new_message}"
            logging.debug("Final Prompt Built Successfully.")
            return final_prompt

        except Exception as e:
            logging.error(f"Error in build_counsellor_prompt: {e}", exc_info=True)
            raise

    # --- Main Logic ---
    try:
        prompt = await build_counsellor_prompt(user, session_id, request.message, db, redis_client)
    except Exception as e:
        logging.error(f"❌ build_counsellor_prompt failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    # Prepare request for LLM
    llm_request = ChatRequest(session_id=session_id, prompt=prompt, language=language)

    response_chunks = []  # Accumulate the full response
    try:
        logging.debug("Sending request to LLM service.")
        async for chunk in chat_logic(llm_request):  # Await the async generator
            logging.debug(f"Received chunk: {chunk}")
            response_chunks.append(chunk)
            yield chunk  # Stream the chunk directly to the client
        logging.debug("Received full response from LLM service.")

    except Exception as e:
        logging.exception(f"Error during LLM processing: {e}")
        error_message = f"LLM Error: {str(e)}" if language == "en" else f"LLM错误: {str(e)}"
        yield error_message # Yield error message to avoid breaking the stream
        raise HTTPException(status_code=500, detail=error_message)

    full_response = "".join(response_chunks)

    # Store message and response *after* receiving the full response
    try:
        counsellor_message = CounsellorMessageHistory(
            user_id=user.id,
            session_id=session_id,
            user_message=request.message,
            counsellor_response=full_response  # Use the accumulated response
        )
        db.add(counsellor_message)
        db.commit()
        db.refresh(counsellor_message)

        # Invalidate cache
        cache_key = f"counsellor_history:{user.id}:{session_id}"
        await redis_client.delete(cache_key)
        logging.debug(f"Cache invalidated: {cache_key}")

    except Exception as e:
        logging.exception(f"Error during database operation: {e}")
        error_message = f"Database Error: {str(e)}" if language == "en" else f"数据库错误: {str(e)}"
        #  Don't re-raise if we've already sent a response
        if not response_chunks: # Only raise if no response was sent
            raise HTTPException(status_code=500, detail=error_message)



    # # Prepare request for LLM
    # llm_request = ChatRequest(session_id=session_id, prompt=prompt, language=language)

    # try:
    #     logging.debug("Sending request to LLM service.")
    #     response = await chat_logic(llm_request) 
    #     logging.debug("Received response from LLM service.")

    #     # Store message and response
    #     counsellor_message = CounsellorMessageHistory(
    #         user_id=user.id,
    #         session_id=session_id,
    #         user_message=request.message,
    #         counsellor_response=response["response"]
    #     )
    #     db.add(counsellor_message)
    #     db.commit()
    #     db.refresh(counsellor_message)

    #     # Invalidate cache
    #     cache_key = f"counsellor_history:{user.id}:{session_id}"
    #     await redis_client.delete(cache_key)
    #     logging.debug(f"Cache invalidated: {cache_key}")

    #     return {
    #         "message": "Response generated successfully" if language == "en" else "回应生成成功",
    #         "response": response["response"]
    #     }

    # except Exception as e:
    #     logging.exception(f"Error during LLM processing: {e}")
    #     raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}" if language == "en" else f"LLM错误: {str(e)}")
