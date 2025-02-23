# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, LargeBinary
from sqlalchemy.orm import relationship

from app.data.database import Base
from app.models.user_prompt import UserPrompt
from app.models.tarot_reading_history import TarotReadingHistory
from app.models.counsellor_message_history import CounsellorMessageHistory

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(LargeBinary, nullable=False)
    is_active = Column(Boolean, default=True)

    #  Add the relationship to TarotReading and CounsellorMessage
    tarot_readings_history = relationship("TarotReadingHistory", back_populates="user")
    counsellor_messages_history = relationship("CounsellorMessageHistory", back_populates="user")
    user_prompts = relationship("UserPrompt", back_populates="user")  # Changed to user_prompts (plural)