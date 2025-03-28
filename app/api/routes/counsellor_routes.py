from fastapi import APIRouter, HTTPException, Depends, Request 
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.data.database import get_db
from app.core.dependencies import get_redis_client
from app.models.counsellor_models import CounsellorChatRequest
from app.services.counsellor_services import analyse_counsellor_request
from app.services.auth_services import get_current_user_from_cookie
from app.models.database_models.user import User


router = APIRouter()

@router.post("/chat")
async def chat(
    request: CounsellorChatRequest,
    db: AsyncSession = Depends(get_db), 
    redis_client: Redis = Depends(get_redis_client),
    user: User | None = Depends(get_current_user_from_cookie),
):
    """
    Handle user chat with LLM session management.
    """
    try:
        # print(f"User:{user}")
        return StreamingResponse(analyse_counsellor_request(request, db, redis_client, user), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

