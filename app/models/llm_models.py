# app/models/llm_models.py
from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    session_id: str
    prompt: str
    model: str = None
    system_instruction: str | None = None
    temperature: float = 0.7


class SummaryRequest(BaseModel):
    conversation_history: str
    model: Optional[str] = None

class ReflectionRequest(BaseModel):
    summary: str
    user_id: int
    model: Optional[str] = None

class PlanRequest(BaseModel):
    summary: str
    reflection: str
    model: Optional[str] = None

