# app/models/user.py

from sqlalchemy import Column, Integer, String, Boolean, LargeBinary
from sqlalchemy.orm import relationship

from app.data.database import Base  # Corrected import


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(LargeBinary, nullable=False)
    is_active = Column(Boolean, default=True)

    #  Add the relationship to TarotReading
    tarot_readings = relationship("TarotReading", back_populates="user")