# app/models/database_models/user_reflection.py

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.data.database import Base


class UserReflection(Base):
    __tablename__ = "user_reflections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    reflection_text = Column(Text, nullable=False)
    reflection_type = Column(String, nullable=True)
    importance_score = Column(Integer, nullable=True)
    embedding = Column(Vector(384), nullable=True)

    user = relationship("User", back_populates="user_reflections")