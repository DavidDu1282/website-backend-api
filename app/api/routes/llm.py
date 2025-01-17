from fastapi import APIRouter, HTTPException
from app.models.llm import ChatRequest
from app.services.llm_service import chat_logic

router = APIRouter()

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Handle user chat with LLM session management.
    """
    try:
        return chat_logic(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
