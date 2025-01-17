from fastapi import APIRouter, HTTPException
from app.models.tarot import TarotAnalysisRequest
from app.services.tarot_service import analyze_tarot_logic

router = APIRouter()

@router.post("/analyze")
async def analyze_tarot(request: TarotAnalysisRequest):
    """
    Analyze the tarot draw results in the context of the user's query.
    """
    try:
        return analyze_tarot_logic(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
