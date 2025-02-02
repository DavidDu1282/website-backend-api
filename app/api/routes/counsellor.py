from fastapi import APIRouter, HTTPException
from app.models.counsellor import ChatRequest
from app.services.counsellor_service import analyse_counsellor_request

router = APIRouter()

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Handle user chat with LLM session management.
    """
    try:
        return analyse_counsellor_request(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
