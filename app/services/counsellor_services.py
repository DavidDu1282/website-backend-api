# app/services/counsellor_service.py
import json
import logging
from typing import List, AsyncGenerator

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.models.llm_models import ChatRequest  # Changed to correct import
from app.models.database_models.user import User
from app.services.llm.llm_services import chat_logic  # Import your LLM service
from app.services.database import database_services  # Import the database service
from app.services.database.counsellor_database_services import get_latest_counsellor_prompt, get_counsellor_messages, create_counsellor_message
from app.services.database.embedding_database_services import retrieve_similar_importance_recent_messages # Import new function

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
    # Get system instruction.  This is now used *only* for the LLM call, not in the prompt itself.
    system_instruction = system_messages.get(language, system_messages["en"])


    async def build_counsellor_prompt(user: User, session_id: str, new_message: str, db: Session, redis_client: Redis) -> str:
        """Builds the complete prompt for the counsellor, using embedding-based retrieval."""
        try:
            logging.debug(f"Building counsellor prompt for user: {user.username}, session: {session_id}")

            # --- Get Custom Prompt ---
            custom_prompt_obj = get_latest_counsellor_prompt(db, user.id)
            custom_prompt = custom_prompt_obj.prompt_text if custom_prompt_obj else ""

            # --- Get Relevant Message History using Embeddings ---
            relevant_messages = retrieve_similar_importance_recent_messages(
                db=db,
                query_text=new_message,
                table_name="counsellor_message_history",
                embedding_column_name="embedding",
                return_column_names=["user_message", "counsellor_response", "importance_score"], # Include importance_score
                top_k=5,  # Adjust as needed
                recency_days=90,  # Example recency
                similarity_weight=0.3, # Example
                importance_weight=0.5, # Example
                recency_weight=0.2, # Example
            )
            # --- Format Relevant History ---
            # Sort by combined_score if you want the absolute best, even if they aren't in chronological order
            # relevant_messages.sort(key=lambda x: x["combined_score"], reverse=True)

            #  OR:  Keep chronological order within the retrieved messages:
            # Fetch 'creation_timestamp' and sort by that if you want to present the *most relevant*
            # messages, but still keep them *roughly* in order.
            # relevant_messages = retrieve_similar_importance_recent_messages(..., return_column_names=["user_message", "counsellor_response", "creation_timestamp"])
            # relevant_messages.sort(key=lambda x: x["creation_timestamp"], reverse=False) # Or reverse=True for newest first

            history_string = "\n".join(
                [f"User: {msg['user_message']}\nCounsellor: {msg['counsellor_response']}"
                for msg in relevant_messages]
            )


            # --- Combine Everything ---
            #final_prompt = f"{base_prompt}\n{custom_prompt}\n\nRelevant Message History:\n{history_string}\n\nUser: {new_message}"
            final_prompt = f"{custom_prompt}\n\nRelevant Message History:\n{history_string}\n\nUser: {new_message}" #Removed base prompt

            logging.debug("Final Prompt Built Successfully.")
            logging.debug(f"Final Prompt: {final_prompt}")
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
    # llm_request = ChatRequest(session_id=session_id, prompt=prompt, language=language) # Before
    llm_request = ChatRequest(session_id=session_id, prompt=prompt, language=language, system_instruction=system_instruction) # Now with system_instruction


    response_chunks = []  # Accumulate the full response
    try:
        logging.debug("Sending request to LLM service.")
        async for chunk in chat_logic(llm_request):  # Await the async generator
            # logging.debug(f"Received chunk: {chunk}")
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
        create_counsellor_message(db, user.id, session_id, request.message, full_response) # Use DB service
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