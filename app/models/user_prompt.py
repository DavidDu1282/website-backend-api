# app/models/user_prompt.py (example)

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.data.database import Base


class UserPrompt(Base):
    __tablename__ = "user_prompts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, server_default=func.now())
    prompt_text = Column(Text, nullable=False)
    prompt_type = Column(String, nullable=False) # e.g., "counsellor", "tarot"

    user = relationship("User", back_populates="user_prompts")