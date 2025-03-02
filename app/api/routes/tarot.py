from fastapi import APIRouter, Depends, HTTPException, Request
from app.models.tarot import TarotAnalysisRequest
from app.services.tarot_service import analyze_tarot_logic
from sqlalchemy.orm import Session
from app.data.database import get_db
from app.models.tarot_reading_history import TarotReadingHistory
from app.services.auth_service import get_current_user_from_cookie

router = APIRouter()

@router.post("/analyze")
async def analyze_tarot(
    request: TarotAnalysisRequest,
    user: str | None = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    """
    Analyze the tarot draw results in the context of the user's query.
    """
    try:
        print(request)
        return analyze_tarot_logic(request, db=db, user=user)  # Pass db and user_id
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/history")
def get_tarot_history(user_id: str = Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    """Fetch a user's tarot reading history."""
    readings = db.query(TarotReadingHistory).filter(TarotReadingHistory.user_id == user_id).order_by(TarotReadingHistory.date.desc()).all()
    
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
def delete_tarot_reading(reading_id: int, user_id: str = Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    """Delete a specific tarot reading."""
    reading = db.query(TarotReadingHistory).filter(TarotReadingHistory.id == reading_id, TarotReadingHistory.user_id == user_id).first()
    
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")

    db.delete(reading)
    db.commit()
    
    return {"message": "Reading deleted successfully"}