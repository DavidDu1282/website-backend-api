from pydantic import BaseModel

class ChatRequest(BaseModel):
    session_id: str
    prompt: str
    model: str = None
