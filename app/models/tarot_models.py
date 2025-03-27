from pydantic import BaseModel
from typing import List

class TarotCard(BaseModel):
    name: str
    orientation: str

class TarotAnalysisRequest(BaseModel):
    session_id: str
    spread: str
    tarot_cards: List[TarotCard]
    user_context: str
    language: str