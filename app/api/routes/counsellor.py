from fastapi import APIRouter, HTTPException, Depends, Request 
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from redis.asyncio import Redis
from app.data.database import get_db
from app.core.dependencies import get_redis_client
from app.models.counsellor import ChatRequest
from app.services.counsellor_service import analyse_counsellor_request
from app.services.auth_service import get_current_user_from_cookie

router = APIRouter()

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db), 
    redis_client: Redis = Depends(get_redis_client),
    # fastapi_req: Request = Depends(),
    user: str | None = Depends(get_current_user_from_cookie),
):
    """
    Handle user chat with LLM session management.
    """
    try:
        # print(f"User:{user}")
        return StreamingResponse(analyse_counsellor_request(request, db, redis_client, user), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

