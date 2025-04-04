# app/api/routes/bagua_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_redis_client
from app.data.database import get_db

from app.models.llm_models import ChatRequest
from app.services.auth_services import get_current_user_from_cookie
from app.services.bagua_services import analyze_bagua_request

router = APIRouter()

@router.post("/analyze")
async def analyze_bagua(
    request: ChatRequest,
    user: str | None = Depends(get_current_user_from_cookie),
    redis_client: Redis = Depends(get_redis_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a Bagua-related query.  The user provides their question/context.
    """
    try:
        return StreamingResponse(analyze_bagua_request(request, db=db, user=user), media_type="text/plain")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
