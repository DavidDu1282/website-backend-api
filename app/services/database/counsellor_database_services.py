# app/services/counsellor_services.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc, asc
from app.models.database_models.counsellor_message_history import CounsellorMessageHistory
from app.models.database_models.user_prompt import UserPrompt
from app.services.database.embedding_database_services import generate_embedding, retrieve_similar_messages  # Import from embedding_services
from app.services.database.importance_database_services import calculate_overall_importance
from app.models.llm_models import ChatRequest
from app.services.llm.llm_services import chat_logic
import logging
import numpy as np

import re

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


# Configure logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)  # Set the desired logging level for this module.
# If you've already configured logging at the top level, you can omit this:
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def create_counsellor_message(
    db: Session,
    user_id: int,
    session_id: str,
    user_message: Optional[str] = None,
    counsellor_response: Optional[str] = None,
    similarity_threshold: float = 0.8,  # Pass through to importance function
    top_k: int = 10,  # Pass through to importance function
    placeholder_value: float = 0.0,  # Pass through to importance function
) -> CounsellorMessageHistory:
    """
    Creates a new counsellor message record, calculating and storing importance.

    Args:
        db: The database session.
        user_id: The ID of the user.
        session_id: The session ID associated with the message.
        user_message: The user's message (can be None).
        counsellor_response: The counsellor's response (can be None).
        similarity_threshold:  For calculate_overall_importance.
        top_k:  For calculate_overall_importance.
        placeholder_value: For calculate_overall_importance.

    Returns:
        The newly created CounsellorMessageHistory object.

    Raises:
        ValueError: If both user_message and counsellor_response are None.
        SQLAlchemyError: If a database error occurs (after logging and rollback).
    """
    log.debug(f"Entering create_counsellor_message with user_id={user_id}, session_id={session_id}, "
              f"user_message='{user_message}', counsellor_response='{counsellor_response}'")

    if user_message is None and counsellor_response is None:
        log.error("Both user_message and counsellor_response are None.  Raising ValueError.")
        raise ValueError("At least one of user_message or counsellor_response must be provided.")

    try:
        embedding = generate_embedding(user_message) if user_message else None
        # log.debug(f"Generated embedding: {embedding}")


        # Calculate importance score if there's a user message
        importance_score = (
            calculate_overall_importance(db, user_message, similarity_threshold, top_k, placeholder_value)
            if user_message
            else None  # Set to None if no user message
        )
        log.debug(f"Calculated importance_score: {importance_score}")

        if embedding is not None:
            embedding_array = np.array(embedding)
        else:
            embedding_array = None  # Handle cases where no embedding is provided
        # log.debug(f"Embedding as NumPy array: {embedding_array}")


        new_message = CounsellorMessageHistory(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            counsellor_response=counsellor_response,
            embedding=embedding_array,
            importance_score=importance_score,
        )
        log.debug(f"Created CounsellorMessageHistory object: {new_message}")

        db.add(new_message)
        log.debug("Added new_message to the database session.")

        db.flush()  # Flush *before* the commit, to catch errors earlier.
        log.debug("Flushed the database session.")

        db.commit()
        log.debug("Committed the database transaction.")

        db.refresh(new_message)
        log.debug(f"Refreshed new_message: {new_message}")

        return new_message

    except SQLAlchemyError as e:
        log.error(f"SQLAlchemyError during create_counsellor_message: {e}", exc_info=True)
        db.rollback()
        log.debug("Rolled back the database transaction due to SQLAlchemyError.")
        raise  # Re-raise the exception

    except Exception as e:
        log.exception(f"Unexpected error during create_counsellor_message: {e}") #exc_info=True also works
        db.rollback()
        log.debug("Rolled back the database transaction due to unexpected error.")
        raise
    finally:
        log.debug("Exiting create_counsellor_message")

def get_similar_counsellor_responses(db, user_message: str, top_n: int = 5):
    """
    Gets similar counsellor message history based on a user's message.
    """
    table_name = "counsellor_message_history"  # Or your table name
    embedding_column = "embedding"  # Your embedding column
    return_columns = ["user_message", "counsellor_response"]  # What to get back

    similar_messages = retrieve_similar_messages(
        db=db,  # Pass the database session
        query_text=user_message,  # The user's input
        table_name=table_name,
        embedding_column_name=embedding_column,
        return_column_names=return_columns,
        top_k=top_n,
    )

    return similar_messages

def delete_counsellor_message(db: Session, message_id: int) -> None:
    """Deletes a specific counsellor message by its ID."""
    message = db.query(CounsellorMessageHistory).filter(CounsellorMessageHistory.id == message_id).first()
    if message:
        db.delete(message)
        db.commit()

def get_latest_counsellor_prompt(db: Session, user_id: int) -> Optional[UserPrompt]:
    """Retrieves the latest counsellor prompt for a user."""
    return db.query(UserPrompt).filter(
        UserPrompt.user_id == user_id,
        UserPrompt.prompt_type == "counsellor"
    ).order_by(UserPrompt.timestamp.desc()).first()
