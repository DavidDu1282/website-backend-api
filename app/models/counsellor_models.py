from pydantic import BaseModel

class CounsellorChatRequest(BaseModel):
    session_id: str
    private_session: bool = False
    message: str
    language: str
