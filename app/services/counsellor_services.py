# app/services/counsellor_services.py
import logging
from typing import AsyncGenerator
from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy.orm import Session
from app.models.llm_models import ChatRequest
from app.models.database_models.user import User
from app.services.llm.llm_services import chat_logic
from app.services.database.counsellor_database_services import get_latest_counsellor_prompt, create_counsellor_message, get_similar_importance_recent_counsellor_responses
import time
import asyncio

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def analyse_counsellor_request(request: ChatRequest, db: Session, redis_client: Redis, user: User) -> AsyncGenerator[str, None]:
    """
    Analyzes user input, generates LLM response, manages caching.
    Streams the response, measures time to first chunk.
    """
    request_received_time = time.time()  # Time when request enters the function
    logging.debug("Starting analyse_counsellor_request")

    # ... (rest of your setup code: validation, language, session_id, etc.) ...
    if not request.message or not request.message.strip():
        logging.warning("Invalid input: Message cannot be empty")
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    language = request.language if request.language else "en"
    session_id = request.session_id if request.session_id else "default"

    system_messages = {
        "en": "Provide concise, supportive advice as a helpful and empathetic counselor.",
        "zh": "你是一位乐于助人且富有同情心的咨询师。请提供简洁、支持性的建议。",
        "zh_TW": "你是一位樂於助人且具同理心的諮詢師。請提供簡潔、支持性的建議。"
    }
    system_instruction = system_messages.get(language, system_messages["en"])

    async def build_counsellor_prompt(user: User, session_id: str, new_message: str, db: Session, redis_client: Redis) -> str:
        """Builds the complete prompt, using embedding-based retrieval and Redis."""
        try:
            logging.debug(f"Building counsellor prompt for user: {user.username}, session: {session_id}")
            prompt_build_start = time.time()

            custom_prompt_start = time.time()
            custom_prompt_obj = get_latest_counsellor_prompt(db, user.id)
            custom_prompt = custom_prompt_obj.prompt_text if custom_prompt_obj else ""
            custom_prompt_end = time.time()
            logging.debug(f"  Time to get custom prompt: {custom_prompt_end - custom_prompt_start:.4f} seconds")

            embedding_start = time.time()
            relevant_messages = get_similar_importance_recent_counsellor_responses(
                db=db,
                user_id=user.id,
                user_message=new_message,
                top_n=5)
            embedding_end = time.time()
            logging.debug(f"  Time for embedding retrieval: {embedding_end - embedding_start:.4f} seconds")
            logging.debug(f"  Number of relevant messages found: {len(relevant_messages)}")

            format_db_start = time.time()
            history_string_db = "\n".join(
                [f"User: {msg['user_message']}\nCounsellor: {msg['counsellor_response']}"
                 for msg in relevant_messages]
            )
            format_db_end = time.time()
            logging.debug(f"  Time to format DB history: {format_db_end - format_db_start:.4f} seconds")

            redis_start = time.time()
            cache_key = f"counsellor_history:{user.id}:{session_id}"
            history_list = await redis_client.lrange(cache_key, 0, 9)
            history_string_redis = "\n".join(history_list)

            redis_end = time.time()
            logging.debug(f"  Time for Redis retrieval: {redis_end - redis_start:.4f} seconds")
            logging.debug(f"  Number of messages retrieved from Redis: {len(history_list)}")

            combine_start = time.time()
            final_prompt = f"{custom_prompt}\n\nRecent Message History (Last 10):\n{history_string_redis}\n\nRelevant Message History (From Database):\n{history_string_db}\n\nUser: {new_message}"
            combine_end = time.time()
            logging.debug(f"  Time to combine prompt elements: {combine_end - combine_start:.4f} seconds")

            prompt_build_end = time.time()
            logging.debug(f"Total prompt build time: {prompt_build_end - prompt_build_start:.4f} seconds")
            logging.debug(f"Final Prompt Length: {len(final_prompt)}")

            return final_prompt

        except Exception as e:
            logging.error(f"Error in build_counsellor_prompt: {e}", exc_info=True)
            raise

    try:
        prompt = await build_counsellor_prompt(user, session_id, request.message, db, redis_client)
    except Exception as e:
        logging.error(f"❌ build_counsellor_prompt failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    llm_request = ChatRequest(session_id=session_id, prompt=prompt, language=language, system_instruction=system_instruction)

    response_chunks = []
    try:
        logging.debug("Sending request to LLM service.")
        async for chunk in chat_logic(llm_request):
            response_chunks.append(chunk)
            # --- KEY CHANGE: Measure time to first chunk HERE ---
            if len(response_chunks) == 1:  # Only log on the *first* chunk
                first_chunk_time = time.time()
                time_to_first_chunk = first_chunk_time - request_received_time
                logger.info(f"Time to first chunk (counsellor): {time_to_first_chunk:.4f} seconds")
            yield chunk
            # await asyncio.sleep(0)
        logging.debug("Received full response from LLM service.")

    except Exception as e:
        logging.exception(f"Error during LLM processing: {e}")
        error_message = f"LLM Error: {str(e)}" if language == "en" else f"LLM错误: {str(e)}"
        yield error_message
        raise HTTPException(status_code=500, detail=error_message)

    full_response = "".join(response_chunks)

    try:
        create_counsellor_message(db, user.id, session_id, request.message, full_response)

        cache_key = f"counsellor_history:{user.id}:{session_id}"
        await redis_client.lpush(cache_key, f"User: {request.message}\nCounsellor: {full_response}")
        await redis_client.ltrim(cache_key, 0, 9)
        logging.debug(f"Cache updated: {cache_key}")

    except Exception as e:
        logging.exception(f"Error during database operation: {e}")
        error_message = f"Database Error: {str(e)}" if language == "en" else f"数据库错误: {str(e)}"
        if not response_chunks:
            raise HTTPException(status_code=500, detail=error_message)
        
    end_time = time.time()  # Overall end time
    logger.info(f"Total tarot service time: {end_time - request_received_time:.4f} seconds")
# # app/services/counsellor_services.py
# import logging
# from typing import AsyncGenerator
# from fastapi import HTTPException
# from redis.asyncio import Redis
# from sqlalchemy.orm import Session
# from app.models.llm_models import ChatRequest  # Changed to correct import
# from app.models.database_models.user import User
# from app.services.llm.llm_services import chat_logic  # Import your LLM service
# from app.services.database.counsellor_database_services import get_latest_counsellor_prompt, create_counsellor_message, get_similar_importance_recent_counsellor_responses

# # Configure logging (adjust level and format as needed)
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# async def analyse_counsellor_request(request: ChatRequest, db: Session, redis_client: Redis, user: User) -> AsyncGenerator[str, None]:
#     """
#     Analyzes user input, generates an LLM response, and manages caching.
#     Streams the response back to the client.  Uses Redis for recent history.
#     """
#     logging.debug("Starting analyse_counsellor_request")

#     # Validate user message (more robust check)
#     if not request.message or not request.message.strip():
#         logging.warning("Invalid input: Message cannot be empty")
#         raise HTTPException(status_code=400, detail="Message cannot be empty")

#     language = request.language if request.language else "en"
#     session_id = request.session_id if request.session_id else "default"

#     # Define system messages (clearer structure)
#     system_messages = {
#         "en": "You are a helpful and empathetic counsellor. Provide thoughtful and supportive advice.",
#         "zh": "你是一个乐于助人且富有同情心的咨询师。请提供周到和支持性的建议。",
#         "zh_TW": "你是一個樂於助人且富有同情心的諮詢師。請提供周到和支持性的建議：",
#     }
#     # Get system instruction.  This is now used *only* for the LLM call, not in the prompt itself.
#     system_instruction = system_messages.get(language, system_messages["en"])


#     async def build_counsellor_prompt(user: User, session_id: str, new_message: str, db: Session, redis_client: Redis) -> str:
#         """Builds the complete prompt for the counsellor, using embedding-based retrieval and Redis cache."""
#         try:
#             logging.debug(f"Building counsellor prompt for user: {user.username}, session: {session_id}")

#             # --- Get Custom Prompt ---
#             custom_prompt_obj = get_latest_counsellor_prompt(db, user.id)
#             custom_prompt = custom_prompt_obj.prompt_text if custom_prompt_obj else ""

#             # --- Get Relevant Message History using Embeddings (for older messages) ---
#             relevant_messages = get_similar_importance_recent_counsellor_responses(
#                 db=db,
#                 user_id=user.id,
#                 user_message=new_message,
#                 top_n=5)  # Fetch fewer from DB, as we have Redis now

#             # --- Format Relevant History (from DB) ---
#             history_string_db = "\n".join(
#                 [f"User: {msg['user_message']}\nCounsellor: {msg['counsellor_response']}"
#                 for msg in relevant_messages]
#             )

#             # --- Get Recent Message History from Redis ---
#             cache_key = f"counsellor_history:{user.id}:{session_id}"
#             history_list = await redis_client.lrange(cache_key, 0, 9)  # Get last 10 messages
#             history_string_redis = "\n".join(history_list)


#             # --- Combine Everything ---
#             final_prompt = f"{custom_prompt}\n\nRecent Message History (Last 10):\n{history_string_redis}\n\nRelevant Message History (From Database):\n{history_string_db}\n\nUser: {new_message}"

#             logging.debug("Final Prompt Built Successfully.")
#             logging.debug(f"Final Prompt: {final_prompt}") #Might be very large now, consider removing for prod
#             return final_prompt

#         except Exception as e:
#             logging.error(f"Error in build_counsellor_prompt: {e}", exc_info=True)
#             raise

#     # --- Main Logic ---
#     try:
#         prompt = await build_counsellor_prompt(user, session_id, request.message, db, redis_client)
#     except Exception as e:
#         logging.error(f"❌ build_counsellor_prompt failed: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=str(e))

#     # Prepare request for LLM
#     llm_request = ChatRequest(session_id=session_id, prompt=prompt, language=language, system_instruction=system_instruction)


#     response_chunks = []  # Accumulate the full response
#     try:
#         logging.debug("Sending request to LLM service.")
#         async for chunk in chat_logic(llm_request):  # Await the async generator
#             response_chunks.append(chunk)
#             yield chunk  # Stream the chunk directly to the client
#         logging.debug("Received full response from LLM service.")

#     except Exception as e:
#         logging.exception(f"Error during LLM processing: {e}")
#         error_message = f"LLM Error: {str(e)}" if language == "en" else f"LLM错误: {str(e)}"
#         yield error_message # Yield error message to avoid breaking the stream
#         raise HTTPException(status_code=500, detail=error_message)

#     full_response = "".join(response_chunks)

#     # Store message and response *after* receiving the full response
#     try:
#         create_counsellor_message(db, user.id, session_id, request.message, full_response) # Use DB service

#         # --- Update Redis Cache ---
#         cache_key = f"counsellor_history:{user.id}:{session_id}"
#         await redis_client.lpush(cache_key, f"User: {request.message}\nCounsellor: {full_response}")
#         await redis_client.ltrim(cache_key, 0, 9)  # Keep only the last 10 entries
#         logging.debug(f"Cache updated: {cache_key}")


#     except Exception as e:
#         logging.exception(f"Error during database operation: {e}")
#         error_message = f"Database Error: {str(e)}" if language == "en" else f"数据库错误: {str(e)}"
#         #  Don't re-raise if we've already sent a response
#         if not response_chunks: # Only raise if no response was sent
#             raise HTTPException(status_code=500, detail=error_message)
