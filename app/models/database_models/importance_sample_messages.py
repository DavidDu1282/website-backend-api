# app/models/database_models/importance_sample_messages.py
from sqlalchemy import Column, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY, FLOAT
from app.data.database import Base  # Corrected import
from pgvector.sqlalchemy import Vector  # Import the Vector type

class ImportanceSampleMessages(Base):
    __tablename__ = "importance_sample_messages"

    sample_message = Column(Text, primary_key=True)  # Store the sample message
    importance_score = Column(Integer) # Store the importance score of the message
    # embedding = Column(ARRAY(FLOAT))
    embedding = Column(Vector(384), nullable=True)
