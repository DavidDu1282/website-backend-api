# app/api/routes/llm_routes.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_redis_client
from app.data.database import get_db

from app.models.database_models.user import User
from app.models.llm_models import ChatRequest
from app.services.auth_services import get_current_user_from_cookie
from app.services.llm.llm_services import chat_logic

router = APIRouter()

@router.post("/chat")
async def chat(request: ChatRequest,
    db: AsyncSession = Depends(get_db), 
    redis_client: Redis = Depends(get_redis_client),
    user: User | None = Depends(get_current_user_from_cookie),):
    """
    Handle user chat with LLM session management, streaming the response.
    """
    try:
        return StreamingResponse(chat_logic(request, db, redis_client, "dummy_user_id"), media_type="text/event-stream")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))