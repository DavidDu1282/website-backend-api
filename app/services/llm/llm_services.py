# app/services/llm/llm_service.py
import asyncio
from typing import AsyncGenerator, Optional, Dict, Union
import httpx
# from app.services.llm.gemini_services import (  # Remove gemini-specific imports
#     query_gemini_api,
#     get_available_gemini_model,
#     reset_gemini_rate_limits,
#     GEMINI_MODELS,
#     is_gemini_model_available,
# )
# from app.services.llm.vertex_services import (  # Remove vertex-specific imports
#     query_vertex_ai_api,
#     cleanup_expired_vertex_sessions,
# )
from app.services.llm.llm_utils import ( # Import from the new file
    query_genai_api,
    cleanup_expired_sessions,
    GEMINI_MODELS,
)
from app.models.llm_models import ChatRequest, SummaryRequest, ReflectionRequest, PlanRequest  # Import request models


async def chat_logic(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Handles LLM chat sessions, allowing the use of both Vertex AI and Gemini APIs.
    Prioritizes based on user selection, then availability.
    """
    user_selected_model = request.model

    cleanup_expired_sessions()  # Centralized cleanup

    # --- Model Selection Logic ---
    if user_selected_model:
        if user_selected_model in GEMINI_MODELS:
            async for chunk in query_genai_api(request=request, model_name=user_selected_model):
                await asyncio.sleep(0)
                yield chunk
            return
        else:  # Invalid model selection
            yield f"Error: Invalid model selected: {user_selected_model}. Trying other models..."

    # --- Fallback Logic (if no user selection or selected model fails) ---
    # Iterate through available models, trying each one
    for model_name, _ in GEMINI_MODELS.items():
        try:
            async for chunk in query_genai_api(request=request, model_name=model_name):
                await asyncio.sleep(0)
                yield chunk
            return  # If successful, exit the function
        except Exception as e:
            print(f"Model {model_name} failed: {e}")  # Log the failure
            continue # Try the next model

    # --- All models failed ---
    yield "Error: All models are unavailable or have exceeded their rate limits. Try again later."


async def _llm_query_helper(prompt: str, model: Optional[str] = None) -> str:
    """Helper function to query LLMs, reusing chat_logic's model selection."""

    # Create a dummy ChatRequest
    request = ChatRequest(session_id="dummy_session", prompt=prompt, model=model)
    response_generator = chat_logic(request)

    full_response = ""
    async for chunk in response_generator:
        full_response += chunk  # Accumulate the chunks

    return full_response

# async def generate_summary(request: SummaryRequest) -> str:
#     """Generates a summary of the conversation history."""
#     prompt = f"""Summarize the following conversation:

#     Conversation History:
#     {request.conversation_history}

#     Summary:"""
#     return await _llm_query_helper(prompt, request.model)


async def generate_reflection(request: ReflectionRequest) -> str:
    """Generates a reflection directly from the conversation history."""
    prompt = f"""Based on the following conversation history of a user's interactions with an AI counsellor, generate a thoughtful reflection:

      Conversation History:
      {request.conversation_history}

      User ID: {request.user_id}
      Reflection:
      """
    return await _llm_query_helper(prompt, request.model)


async def generate_plan(request: PlanRequest) -> str:
    """Generates a plan for the next conversation."""
    prompt = f"""Based on the following reflection and summary, create a plan for the AI counsellor's next conversation with the user.

        Reflection: {request.reflection}
        Summary: {request.summary}

        Plan for Next Conversation:
        - Topics to Explore:
        - Questions to Ask:
        - Techniques to Consider:
        - Goals for the session:"""
    return await _llm_query_helper(prompt, request.model)



async def generate_reflection_and_plan(conversation_history: str, user_id: int, model: Optional[str] = None) -> Dict[str, str]:
    """Generates a reflection and plan, handling potential errors."""
    try:
        summary_request = SummaryRequest(conversation_history=conversation_history, model=model)
        summary = await generate_summary(summary_request)

        reflection_request = ReflectionRequest(summary=summary, user_id=user_id, model=model)
        reflection = await generate_reflection(reflection_request)

        plan_request = PlanRequest(summary=summary, reflection=reflection, model=model)
        plan = await generate_plan(plan_request)

        return {"reflection": reflection, "plan": plan}

    except Exception as e:
        print(f"Error during reflection/plan generation: {e}")
        return {"error": str(e)}


# # app/services/llm/llm_service.py
# import asyncio
# from typing import AsyncGenerator, Optional, Dict, Union
# import httpx
# from app.services.llm.gemini_services import (
#     query_gemini_api,
#     get_available_gemini_model,
#     reset_gemini_rate_limits,
#     GEMINI_MODELS,
#     is_gemini_model_available,
# )
# from app.services.llm.vertex_services import (
#     query_vertex_ai_api,
#     cleanup_expired_vertex_sessions,
# )
# from app.models.llm_models import ChatRequest, SummaryRequest, ReflectionRequest, PlanRequest  # Import request models


# async def chat_logic(request: ChatRequest) -> AsyncGenerator[str, None]:
#     """
#     Handles LLM chat sessions, allowing the use of both Vertex AI and Gemini APIs.
#     Prioritizes based on user selection, then availability.
#     """
#     session_id = request.session_id
#     prompt = request.prompt
#     user_selected_model = request.model

#     reset_gemini_rate_limits()  # Now uses the gemini-specific function
#     cleanup_expired_vertex_sessions()

#     # --- Model Selection Logic ---
#     if user_selected_model:
#         if user_selected_model == "vertex-ai":
#             try:
#                 async for chunk in query_vertex_ai_api(request=request):
#                     yield chunk
#                 return
#             except Exception as e:
#                 yield f"Vertex AI Error: {e}.  Falling back to Gemini."

#         elif user_selected_model in GEMINI_MODELS:
#             if is_gemini_model_available(user_selected_model):
#                 async for chunk in query_gemini_api(request=request, model_name=user_selected_model):
#                     yield chunk
#                 return
#             else:
#                 yield f"Error: Model '{user_selected_model}' has exceeded its rate limit.  Trying other models..."

#         else:  # Invalid model selection
#             yield f"Error: Invalid model selected: {user_selected_model}. Trying other models..."

#     # --- Fallback Logic (if no user selection or selected model fails) ---

#     # Try Vertex AI first (if no specific model was requested)
#     if not user_selected_model or (user_selected_model == "vertex-ai"):
#         try:
#             async for chunk in query_vertex_ai_api(request=request):
#                 yield chunk
#             return  # success
#         except Exception as e:
#             print(f"Vertex AI failed: {e}")  # Log the specific error

#     # Try Gemini models (prioritize those not exceeding limits)
#     available_gemini_model = get_available_gemini_model()
#     if available_gemini_model:
#         async for chunk in query_gemini_api(request=request, model_name=available_gemini_model):
#             yield chunk
#         return  # success

#     # --- All models failed ---
#     yield "Error: All models are unavailable or have exceeded their rate limits. Try again later."

# async def _llm_query_helper(prompt: str, model: Optional[str] = None) -> str:
#     """Helper function to query LLMs, reusing chat_logic's model selection."""

#     # Create a dummy ChatRequest
#     request = ChatRequest(session_id="dummy_session", prompt=prompt, model=model)
#     response_generator = chat_logic(request)

#     full_response = ""
#     async for chunk in response_generator:
#         full_response += chunk  # Accumulate the chunks

#     return full_response

# async def generate_summary(request: SummaryRequest) -> str:
#     """Generates a summary of the conversation history."""
#     prompt = f"""Summarize the following conversation:

#     Conversation History:
#     {request.conversation_history}

#     Summary:"""
#     return await _llm_query_helper(prompt, request.model)


# async def generate_reflection(request: ReflectionRequest) -> str:
#     """Generates a reflection based on the conversation summary."""
#     prompt = f"""Based on the following summary of a user's interactions with an AI counsellor, generate a thoughtful reflection:

#       Summary: {request.summary}
#       User ID: {request.user_id}
#       Reflection:
#       """
#     return await _llm_query_helper(prompt, request.model)


# async def generate_plan(request: PlanRequest) -> str:
#     """Generates a plan for the next conversation."""
#     prompt = f"""Based on the following reflection and summary, create a plan for the AI counsellor's next conversation with the user.

#         Reflection: {request.reflection}
#         Summary: {request.summary}

#         Plan for Next Conversation:
#         - Topics to Explore:
#         - Questions to Ask:
#         - Techniques to Consider:
#         - Goals for the session:"""
#     return await _llm_query_helper(prompt, request.model)



# async def generate_reflection_and_plan(conversation_history: str, user_id: int, model: Optional[str] = None) -> Dict[str, str]:
#     """Generates a reflection and plan, handling potential errors."""
#     try:
#         summary_request = SummaryRequest(conversation_history=conversation_history, model=model)
#         summary = await generate_summary(summary_request)

#         reflection_request = ReflectionRequest(summary=summary, user_id=user_id, model=model)
#         reflection = await generate_reflection(reflection_request)

#         plan_request = PlanRequest(summary=summary, reflection=reflection, model=model)
#         plan = await generate_plan(plan_request)

#         return {"reflection": reflection, "plan": plan}

#     except Exception as e:
#         print(f"Error during reflection/plan generation: {e}")
#         return {"error": str(e)}