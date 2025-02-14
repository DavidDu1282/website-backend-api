# app/models/tarot_reading.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.data.database import Base  # Corrected import


class TarotReading(Base):
    __tablename__ = "tarot_readings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    reading_date = Column(DateTime)
    cards_drawn = Column(String)  # Or a JSON column, etc.
    interpretation = Column(String)

    user = relationship("User", back_populates="tarot_readings")