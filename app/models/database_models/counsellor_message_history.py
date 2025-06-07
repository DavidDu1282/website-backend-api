# app/models/database_models/counsellor_message_history.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from pgvector.sqlalchemy import Vector

from app.data.database import Base

class CounsellorMessageHistory(Base):
    __tablename__ = "counsellor_message_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    creation_timestamp = Column(DateTime, server_default=func.now())
    last_updated_timestamp = Column(DateTime, server_default=func.now(), onupdate=func.now())
    user_message = Column(Text, nullable=True)
    counsellor_response = Column(Text, nullable=True)
    session_id = Column(String)
    importance_score = Column(Integer, nullable=True)
    embedding = Column(Vector(384), nullable=True)
    private_message = Column(Boolean, default=False)

    user = relationship("User", back_populates="counsellor_messages_history")