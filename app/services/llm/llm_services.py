# app/services/llm/llm_service.py
import logging
from datetime import datetime
from typing import AsyncGenerator

from google import genai
from google.genai import types

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sessions import chat_sessions
from app.core.startup import llm_clients

from app.models.llm_models import ChatRequest, PlanRequest, ReflectionRequest
from app.services.database.user_database_services import (
    create_user_plan,
    create_or_update_user_reflection,
    get_active_user_plan,
    get_user_reflections,
)
from app.services.llm.llm_utils import (
    GEMINI_MODELS,
    SESSION_EXPIRY_TIME,
    _llm_query_helper,
    query_genai_api,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def chat_logic(request: ChatRequest, db: AsyncSession, redis_client: Redis, user_id: str) -> AsyncGenerator[str, None]:
    """
    Handles LLM chat sessions, allowing the use of both Vertex AI and Gemini APIs.
    Prioritizes based on user selection, then availability. This function manages
    session creation, retrieval, expiry, and delegates the actual query to query_genai_api.
    """

    # cleanup_expired_sessions()

    if request.model:
        if request.model in GEMINI_MODELS:
            try:
                async for chunk in _query_with_session(request, user_id, db):
                    yield chunk
                return
            except Exception as e:
                yield f"Error with selected model {request.model}: {e}. Trying other models..."
        else:
            yield f"Error: Invalid model selected: {request.model}. Trying other models..."

    # --- Fallback Logic (if no user selection or selected model fails) ---
    for model_name, _ in GEMINI_MODELS.items():
        try:
            request.model = model_name
            async for chunk in _query_with_session(request, db, redis_client, user_id):
                yield chunk
            return
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            continue

    yield "Error: All models are unavailable or have exceeded their rate limits. Try again later."

async def _query_with_session(request: ChatRequest, db: AsyncSession, redis_client: Redis, user_id: str) -> AsyncGenerator[str, None]:
    """
    Manages the chat session lifecycle and calls the underlying query_genai_api.
    """
    if request.model not in GEMINI_MODELS:
        yield f"Error: Model '{request.model}' not found."
        return

    model_config = GEMINI_MODELS[request.model]
    model_type = model_config["type"]
    global redis
    try:
        if request.session_id in chat_sessions:
            session_data = chat_sessions[request.session_id]
            chat_session = session_data["chat_session"]
            if datetime.now() - session_data["last_used"] > SESSION_EXPIRY_TIME:
                await close_session(request.session_id, db, redis_client)
                chat_session = await start_new_chat_session(request, llm_clients[model_type], db, user_id)
        else:
            chat_session = await start_new_chat_session(request, llm_clients[model_type], db, user_id)

        chat_sessions[request.session_id]["last_used"] = datetime.now()

        async for chunk in query_genai_api(request):
            yield chunk

    except Exception as e:
        print(f"Error in _query_with_session: {e}")
        yield f"An error occurred during processing: {e}"


async def generate_reflection(request: ReflectionRequest) -> str:
    """Generates a reflection directly from the conversation history."""
    prompt = f"""Based on the following conversation history of a user's interactions with an AI counsellor, generate a thoughtful reflection. Please use a third person's perspective.:

      Conversation History:
      {request.conversation_history}

      User ID: {request.user_id}
      Reflection:
      """
    return await _llm_query_helper(prompt, request.model)


async def generate_plan(request: PlanRequest, db, user_id) -> str:
    """Generates a plan for the next conversation."""
    previous_plan = await get_active_user_plan(db, user_id)
    prompt = f"""Based on the following reflection and previous plan, create a plan for the AI counsellor's next conversation with the user.

        Previous Plan: {previous_plan}
        Reflection: {request.reflection}

        Plan for Next Conversation:
        - Priority Topics to Explore: (List of 1-3 key topics, prioritized based on urgency, emotional impact, or overall goals)
        - Specific Questions to Ask: (Open-ended questions designed to encourage deeper exploration of the prioritized topics)
        - Techniques to Consider: (Specific counseling techniques that might be helpful, e.g., active listening, summarizing, reframing, validation, cognitive restructuring)
        - Potential Challenges and Mitigation Strategies: (Anticipate potential roadblocks and brainstorm ways to overcome them)
        - Goals for the session: (What the user hopes to achieve or gain from the conversation - be as specific as possible.)
        """
    return await _llm_query_helper(prompt, request.model)


async def start_new_chat_session(request: ChatRequest, client: genai.Client, db: AsyncSession, user_id: str):
    """Starts a new chat session."""
    try:
        logger.debug(f"Starting new chat session for user {user_id}, with model {request.model}")
        plan = await get_active_user_plan(db, user_id)
        logger.debug(f"Plan for new chat session: {plan}")
        chat_session = client.chats.create(model=request.model, config=types.GenerateContentConfig(system_instruction=plan))
        chat_sessions[request.session_id] = {
            "chat_session": chat_session,
            "last_used": datetime.now(),
            "user_id": user_id
        }
        return chat_session
    except Exception as e:
        print(f"Error starting session: {e}")
        raise


async def close_session(session_id: str, db: AsyncSession, redis_client: Redis):
    """Closes a chat session, generates a reflection based on the conversation history, and generates a new plan for the user."""
    if session_id in chat_sessions:
        session_data = chat_sessions[session_id]
        user_id = session_data['user_id']
        logger.debug(f"Closing session {session_id} for user {user_id}")

        cache_key = f"counsellor_history:{user_id}:{session_id}"
        history_list = await redis_client.lrange(cache_key, 0, -1)
        conversation_history = "\n".join(history_list)

        if conversation_history:
            try:
                reflection_request = ReflectionRequest(
                    conversation_history=conversation_history,
                    user_id=user_id,
                    model="gemini-2.0-flash-lite"
                )
                reflection = await generate_reflection(reflection_request)
                logger.debug(f"Generated reflection for session {session_id}")

                if reflection:
                   await create_or_update_user_reflection(db, user_id, reflection)
                   logger.debug(f"Reflection for session {session_id} saved to database.")
                else:
                    logger.warning(f"Reflection generation returned None for session {session_id}")

            except Exception as e:
                logger.exception(f"Error generating or saving reflection for session {session_id}: {e}")
        else:
            logger.info(f"No conversation history found for session {session_id}, skipping reflection.")
        
        recent_reflections = await get_user_reflections(db, user_id, limit=5)
        combined_reflections = "\n\n".join(
            [ref.reflection_text for ref in recent_reflections]
        )

        plan_request = PlanRequest(reflection=combined_reflections, model="gemini-2.0-flash-lite")  # Choose model.  Could be a user preference.
        plan_text = await generate_plan(plan_request, db, user_id)

        logger.debug(f"Generated plan is: {plan_text}")

        if not plan_text:
            return None

        await create_user_plan(db, user_id, plan_text, plan_type="Session End")

        del chat_sessions[session_id]
        logger.debug(f"Session {session_id} closed.")
        return
    else:
        logger.warning(f"Attempted to close non-existent session: {session_id}")


async def cleanup_expired_sessions(db: AsyncSession, redis_client: Redis):
    """Removes expired chat sessions, triggering reflection and plan generation."""
    now = datetime.now()
    expired_sessions = [
        session_id
        for session_id, session_data in chat_sessions.items()
        if now - session_data["last_used"] > SESSION_EXPIRY_TIME
    ]

    for session_id in expired_sessions:
        await close_session(session_id, db, redis_client)

    if expired_sessions:
        print(f"Cleaned up {len(expired_sessions)} expired sessions.")