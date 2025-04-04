# app/services/database/tarot_database_services.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.database import get_db

from app.models.database_models.tarot_reading_history import TarotReadingHistory
from app.models.tarot_models import TarotAnalysisRequest

from app.services.auth_services import get_current_user_from_cookie
from app.services.tarot_services import analyze_tarot_logic

router = APIRouter()

@router.post("/analyze")
async def analyze_tarot(
    request: TarotAnalysisRequest,
    user: str | None = Depends(get_current_user_from_cookie),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze the tarot draw results in the context of the user's query.
    """
    try:
        print(request)
        return StreamingResponse(analyze_tarot_logic(request, db=db, user=user), media_type="text/event-stream")

        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/history")
async def get_tarot_history(user_id: str = Depends(get_current_user_from_cookie), db: AsyncSession = Depends(get_db)):
    """Fetch a user's tarot reading history."""
    result = await db.execute(select(TarotReadingHistory).where(TarotReadingHistory.user_id == user_id).order_by(TarotReadingHistory.date.desc()))
    readings = result.scalars().all()

    return [
        {
            "id": reading.id,
            "date": reading.date.strftime("%Y-%m-%d %H:%M"),
            "spread": reading.spread,
            "cards": reading.cards,
            "user_context": reading.user_context,
            "analysis": reading.analysis
        }
        for reading in readings
    ]

@router.delete("/history/{reading_id}")
async def delete_tarot_reading(reading_id: int, user_id: str = Depends(get_current_user_from_cookie), db: AsyncSession = Depends(get_db)):
    """Delete a specific tarot reading."""
    result = await db.execute(select(TarotReadingHistory).where(TarotReadingHistory.id == reading_id, TarotReadingHistory.user_id == user_id))
    reading = result.scalars().first()

    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    await db.delete(reading)
    await db.commit()
    
    return {"message": "Reading deleted successfully"}