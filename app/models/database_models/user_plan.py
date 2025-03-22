# app/models/database_models/user_plan.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.data.database import Base


class UserPlan(Base):
    __tablename__ = "user_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    plan_text = Column(Text, nullable=False)
    plan_type = Column(String, nullable=True)
    active_plan = Column(Boolean, default=False)

    user = relationship("User", back_populates="user_plans")
    
