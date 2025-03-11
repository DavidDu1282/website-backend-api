from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.database_models.tarot_reading_history import TarotReadingHistory

def get_tarot_readings(db: Session, user_id: int) -> List[TarotReadingHistory]:
    """Retrieves a user's tarot reading history."""
    return db.query(TarotReadingHistory).filter(TarotReadingHistory.user_id == user_id).order_by(TarotReadingHistory.date.desc()).all()

def get_tarot_reading_by_id(db: Session, reading_id: int, user_id: int) -> Optional[TarotReadingHistory]:
    """Retrieves a specific tarot reading by ID and user ID."""
    return db.query(TarotReadingHistory).filter(TarotReadingHistory.id == reading_id, TarotReadingHistory.user_id == user_id).first()

def create_tarot_reading(db: Session, user_id: int, spread: str, cards: str, user_context: str, analysis: str) -> TarotReadingHistory:
    """Creates a new tarot reading record."""
    new_reading = TarotReadingHistory(
        user_id=user_id,
        spread=spread,
        cards=cards,
        user_context=user_context,
        analysis=analysis
    )
    db.add(new_reading)
    db.commit()
    db.refresh(new_reading)
    return new_reading

def delete_tarot_reading(db: Session, reading_id: int, user_id: int) -> None:
    """Deletes a specific tarot reading, checking for user ownership."""
    reading = get_tarot_reading_by_id(db, reading_id, user_id)  # Use helper
    if reading:
        db.delete(reading)
        db.commit()