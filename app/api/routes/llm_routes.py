# app/api/routes/llm.py
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models.llm_models import ChatRequest
from app.services.llm.llm_services import chat_logic

router = APIRouter()

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Handle user chat with LLM session management, streaming the response.
    """
    try:
        return StreamingResponse(chat_logic(request), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))