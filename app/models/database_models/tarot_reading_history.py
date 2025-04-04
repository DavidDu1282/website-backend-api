# app/models/database_models/tarot_reading_history.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.data.database import Base


class TarotReadingHistory(Base):
    __tablename__ = "tarot_reading_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    reading_date = Column(DateTime)
    cards_drawn = Column(String)
    interpretation = Column(Text)
    spread = Column(String)
    user_context = Column(Text)

    user = relationship("User", back_populates="tarot_readings_history")