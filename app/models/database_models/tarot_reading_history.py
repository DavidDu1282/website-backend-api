# app/models/database_models/tarot_reading_history.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.data.database import Base  # Corrected import


class TarotReadingHistory(Base):
    __tablename__ = "tarot_reading_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    reading_date = Column(DateTime)
    cards_drawn = Column(String)  #  Can still use String for JSON
    interpretation = Column(Text)  # Changed to Text for potentially long interpretations
    spread = Column(String)
    user_context = Column(Text) # Changed to Text for potentially long context

    user = relationship("User", back_populates="tarot_readings_history")