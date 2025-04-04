# app/models/database_models/importance_sample_messages.py
from sqlalchemy import Column, Integer, Text

from pgvector.sqlalchemy import Vector

from app.data.database import Base

class ImportanceSampleMessages(Base):
    __tablename__ = "importance_sample_messages"

    sample_message = Column(Text, primary_key=True)
    importance_score = Column(Integer)
    embedding = Column(Vector(384), nullable=True)
