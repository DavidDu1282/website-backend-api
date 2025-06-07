# app/services/database/counsellor_database_services.py
import logging
from typing import List, Optional

import numpy as np
from sqlalchemy import asc, desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models.counsellor_message_history import (
    CounsellorMessageHistory,
)
from app.models.database_models.user_plan import UserPlan
from app.services.database.embedding_database_services import (
    generate_embedding,
    retrieve_similar_importance_recent_messages,
    retrieve_similar_messages,
)
from app.services.database.importance_database_services import (
    calculate_overall_importance,
)

# # Configure logging
# log = logging.getLogger(__name__)
# #log.setLevel(logging.DEBUG)  # Set the desired logging level for this module.
# # If you've already configured logging at the top level, you can omit this:
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def get_counsellor_messages(
    db: AsyncSession, user_id: int, session_id: Optional[str] = None, limit: int = 10, order_by: str = "desc"
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
    query = select(CounsellorMessageHistory).where(CounsellorMessageHistory.user_id == user_id)

    if session_id:
        query = query.where(CounsellorMessageHistory.session_id == session_id)

    if order_by == "asc":
        query = query.order_by(asc(CounsellorMessageHistory.timestamp))
    else:
        query = query.order_by(desc(CounsellorMessageHistory.timestamp))

    result = await db.execute(query.limit(limit))
    return result.scalars().all()

async def create_counsellor_message(
    db: AsyncSession,
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
        embedding = await generate_embedding(user_message) if user_message else None
        importance_score = (
            await calculate_overall_importance(db, user_message, similarity_threshold, top_k, placeholder_value)
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
        await db.flush()
        await db.commit()
        await db.refresh(new_message)
        
        return new_message
    
    except SQLAlchemyError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise

async def get_similar_counsellor_responses(db: AsyncSession, user_id: int, user_message: str, top_n: int = 5):
    """
    Gets similar counsellor message history based on a user's message.
    """
    table_name = "counsellor_message_history"
    embedding_column = "embedding"
    return_columns = ["user_message", "counsellor_response"]

    similar_messages = await retrieve_similar_messages(
        db=db,
        user_id=user_id,
        query_text=user_message,
        table_name=table_name,
        embedding_column_name=embedding_column,
        return_column_names=return_columns,
        top_k=top_n,
    )

    return similar_messages

async def get_similar_importance_recent_counsellor_responses(db: AsyncSession, user_id: int, user_message: str, top_n: int = 5, private_session: bool = False, session_id: str = None):
    """
    Gets similar messages based on importance, similarity, and recency.
    """
    table_name = "counsellor_message_history"
    embedding_column = "embedding"
    return_columns = ["user_message", "counsellor_response", "importance_score"]

    if private_session:
        similar_messages = await retrieve_similar_importance_recent_messages(
            db=db,
            user_id=user_id,
            query_text=user_message,
            table_name=table_name,
            embedding_column_name=embedding_column,
            return_column_names=return_columns,
            top_k=top_n, 
            similarity_weight=0.3,
            importance_weight=0.5,
            recency_weight=0.2,
            additional_filters={"session_id": session_id}
        )
        
    else:
        similar_messages = await retrieve_similar_importance_recent_messages(
            db=db,
            user_id=user_id,
            query_text=user_message,
            table_name=table_name,
            embedding_column_name=embedding_column,
            return_column_names=return_columns,
            top_k=top_n, 
            similarity_weight=0.3,
            importance_weight=0.5,
            recency_weight=0.2,
            additional_filters={"private_message": False}
        )

    return similar_messages

async def delete_counsellor_message(db: AsyncSession, message_id: int) -> None:
    """Deletes a specific counsellor message by its ID."""
    result = await db.execute(select(CounsellorMessageHistory).where(CounsellorMessageHistory.id == message_id))
    message = result.scalars().first()
    if message:
        await db.delete(message)
        await db.commit()

async def get_latest_counsellor_prompt(db: AsyncSession, user_id: int) -> Optional[UserPlan]:
    """Retrieves the latest counsellor prompt for a user."""
    result = await db.execute(select(UserPlan).where(
        UserPlan.user_id == user_id,
        UserPlan.plan_type == "counsellor"
    ).order_by(UserPlan.updated_at.desc()))
    return result.scalars().first()
