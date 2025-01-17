from pydantic import BaseModel
from typing import List, Dict

class TarotCard(BaseModel):
    name: str
    orientation: str  # "upright" or "reversed"

class TarotAnalysisRequest(BaseModel):
    session_id: str
    tarot_cards: List[TarotCard]
    user_context: str
