# app/models/counsellor_message_history.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.data.database import Base  # Corrected import


class CounsellorMessageHistory(Base):
    __tablename__ = "counsellor_message_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, server_default=func.now())  # Automatic timestamp
    user_message = Column(Text, nullable=True)  # Store user's message, can be null
    counsellor_response = Column(Text, nullable=True)   # Store the AI's response, can be null
    session_id = Column(String) # Store the session ID associated with the message

    user = relationship("User", back_populates="counsellor_messages_history")