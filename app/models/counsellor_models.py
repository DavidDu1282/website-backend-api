from pydantic import BaseModel

class CounsellorChatRequest(BaseModel):
    session_id: str
    message: str
    language: str
