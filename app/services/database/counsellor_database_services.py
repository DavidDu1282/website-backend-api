# app/services/database/counsellor_database_services.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc, asc
from app.models.database_models.counsellor_message_history import CounsellorMessageHistory
from app.models.database_models.user_plan import UserPlan
from app.services.database.embedding_database_services import generate_embedding, retrieve_similar_messages, retrieve_similar_importance_recent_messages
from app.services.database.importance_database_services import calculate_overall_importance
from app.models.llm_models import ChatRequest
from app.services.llm.llm_services import chat_logic
import logging
import numpy as np

import re

# # Configure logging
# log = logging.getLogger(__name__)
# #log.setLevel(logging.DEBUG)  # Set the desired logging level for this module.
# # If you've already configured logging at the top level, you can omit this:
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def get_counsellor_messages(
    db: Session, user_id: int, session_id: Optional[str] = None, limit: int = 10, order_by: str = "desc"
) -> List[CounsellorMessageHistory]:
    """
    Retrieves counsellor messages for a user.

    Args:
        db: The database session.
        user_id: The ID of the user.
        session_id: Optional session ID to filter messages.  If None, retrieves all messages.
        limit: The maximum number of messages to retrieve.
        order_by: "asc" for ascending order (oldest first), "desc" for descending (newest first)

    Returns:
        A list of CounsellorMessageHistory objects.
    """
    """Retrieves counsellor messages for a user."""
    query = db.query(CounsellorMessageHistory).filter(CounsellorMessageHistory.user_id == user_id)

    if session_id:
        query = query.filter(CounsellorMessageHistory.session_id == session_id)

    if order_by == "asc":
        query = query.order_by(asc(CounsellorMessageHistory.timestamp))
    else:  # Default to descending
        query = query.order_by(desc(CounsellorMessageHistory.timestamp))

    return query.limit(limit).all()

def create_counsellor_message(
    db: Session,
    user_id: int,
    session_id: str,
    user_message: Optional[str] = None,
    counsellor_response: Optional[str] = None,
    similarity_threshold: float = 0.6,
    top_k: int = 10,
    placeholder_value: float = 0.0,
) -> CounsellorMessageHistory:
    """
    Creates a new counsellor message record, calculating and storing importance.
    """
    if user_message is None and counsellor_response is None:
        raise ValueError("At least one of user_message or counsellor_response must be provided.")
    
    try:
        embedding = generate_embedding(user_message) if user_message else None
        importance_score = (
            calculate_overall_importance(db, user_message, similarity_threshold, top_k, placeholder_value)
            if user_message else None
        )
        
        new_message = CounsellorMessageHistory(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            counsellor_response=counsellor_response,
            embedding=np.array(embedding) if embedding is not None else None,
            importance_score=importance_score,
        )
        
        db.add(new_message)
        db.flush()
        db.commit()
        db.refresh(new_message)
        
        return new_message
    
    except SQLAlchemyError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

def get_similar_counsellor_responses(db: Session, user_id: int, user_message: str, top_n: int = 5):
    """
    Gets similar counsellor message history based on a user's message.
    """
    table_name = "counsellor_message_history"
    embedding_column = "embedding"
    return_columns = ["user_message", "counsellor_response"]

    similar_messages = retrieve_similar_messages(
        db=db,
        user_id=user_id,  # Filter by user ID
        query_text=user_message,
        table_name=table_name,
        embedding_column_name=embedding_column,
        return_column_names=return_columns,
        top_k=top_n,
    )

    return similar_messages

def get_similar_importance_recent_counsellor_responses(db: Session, user_id: int, user_message: str, top_n: int = 5):
    """
    Gets similar messages based on importance, similarity, and recency.
    """
    table_name = "counsellor_message_history"
    embedding_column = "embedding"
    return_columns = ["user_message", "counsellor_response", "importance_score"]

    similar_messages = retrieve_similar_importance_recent_messages(
        db=db,
        user_id=user_id,  # Filter by user ID
        query_text=user_message,
        table_name=table_name,
        embedding_column_name=embedding_column,
        return_column_names=return_columns,
        top_k=top_n,
        # recency_days=90, 
        similarity_weight=0.3,
        importance_weight=0.5,
        recency_weight=0.2,
    )

    return similar_messages

def delete_counsellor_message(db: Session, message_id: int) -> None:
    """Deletes a specific counsellor message by its ID."""
    message = db.query(CounsellorMessageHistory).filter(CounsellorMessageHistory.id == message_id).first()
    if message:
        db.delete(message)
        db.commit()

def get_latest_counsellor_prompt(db: Session, user_id: int) -> Optional[UserPlan]:
    """Retrieves the latest counsellor prompt for a user."""
    return db.query(UserPlan).filter(
        UserPlan.user_id == user_id,
        UserPlan.plan_type == "counsellor"
    ).order_by(UserPlan.updated_at.desc()).first()
