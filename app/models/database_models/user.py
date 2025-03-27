# app/models/database_models/user.py
from sqlalchemy import Column, Integer, String, Boolean, LargeBinary
from sqlalchemy.orm import relationship

from app.data.database import Base
from app.models.database_models.user_plan import UserPlan
from app.models.database_models.tarot_reading_history import TarotReadingHistory
from app.models.database_models.counsellor_message_history import CounsellorMessageHistory
from app.models.database_models.user_reflection import UserReflection

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(LargeBinary, nullable=False)
    is_active = Column(Boolean, default=True)

    tarot_readings_history = relationship("TarotReadingHistory", back_populates="user")
    counsellor_messages_history = relationship("CounsellorMessageHistory", back_populates="user")
    user_plans = relationship("UserPlan", back_populates="user")
    user_reflections = relationship("UserReflection", back_populates="user")