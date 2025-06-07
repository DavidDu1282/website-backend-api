from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.data.database import Base

class CounsellorSession(Base):
    __tablename__ = "counsellor_sessions"

    id = Column(Integer, primary_key=True, index=True)
    counsellor_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=func.now())
    last_activity = Column(DateTime, server_default=func.now(), onupdate=func.now())
    private_session = Column(Boolean, default=False)
    title = Column(String, nullable=True)

    user = relationship("User", back_populates="counsellor_sessions")