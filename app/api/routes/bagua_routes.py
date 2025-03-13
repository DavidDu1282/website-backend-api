# app/api/routes/bagua_routes.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.models.llm_models import ChatRequest  # Reuse the ChatRequest model
from app.services.bagua_services import analyze_bagua_request
from sqlalchemy.orm import Session
from app.data.database import get_db
# from app.models.database_models.bagua_reading_history import BaguaReadingHistory #Need to create this later
from app.services.auth_services import get_current_user_from_cookie

router = APIRouter()

@router.post("/analyze")
async def analyze_bagua(
    request: ChatRequest,  # Reuse the existing ChatRequest model
    user: str | None = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    """
    Analyze a Bagua-related query.  The user provides their question/context.
    """
    try:
        return StreamingResponse(analyze_bagua_request(request, db=db, user=user), media_type="text/plain")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) #More specific error
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# @router.get("/history")
# def get_bagua_history(user_id: str = Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
#     """Fetch a user's Bagua reading history."""
#     readings = db.query(BaguaReadingHistory).filter(BaguaReadingHistory.user_id == user_id).order_by(BaguaReadingHistory.date.desc()).all()
    
#     return [
#         {
#             "id": reading.id,
#             "date": reading.date.strftime("%Y-%m-%d %H:%M"),
#             "user_question": reading.user_question, #Renamed from tarot_routes.py
#             "bagua_analysis": reading.bagua_analysis #Renamed from tarot_routes.py
#         }
#         for reading in readings
#     ]

# @router.delete("/history/{reading_id}")
# def delete_bagua_reading(reading_id: int, user_id: str = Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
#     """Delete a specific Bagua reading from the user's history."""
#     reading = db.query(BaguaReadingHistory).filter(BaguaReadingHistory.id == reading_id, BaguaReadingHistory.user_id == user_id).first()
    
#     if not reading:
#         raise HTTPException(status_code=404, detail="Reading not found")

#     db.delete(reading)
#     db.commit()
    
#     return {"message": "Reading deleted successfully"}