# app/services/database_services/reflection_database_services.py
from typing import List, Optional

import numpy as np
from sqlalchemy import desc, exists, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models.user_reflection import UserReflection
from app.services.database.embedding_database_services import (
    generate_embedding,
    retrieve_similar_importance_recent_messages,
)
from app.services.database.importance_database_services import (
    calculate_overall_importance,
)

async def create_or_update_user_reflection(db: AsyncSession, user_id: int, reflection_text: str, reflection_type: str = "Counsellor", similarity_threshold: float = 0.6, top_k: int = 10, placeholder_value:float=0.0) -> UserReflection:  
    """Creates or updates a user reflection, calculating and storing importance."""
    try:
        embedding = await generate_embedding(reflection_text)
        importance_score = await calculate_overall_importance(db, reflection_text, similarity_threshold, top_k, placeholder_value)

        result = await db.execute(select(UserReflection).filter(UserReflection.user_id == user_id).order_by(UserReflection.updated_at.desc()))
        reflection = result.scalars().first()

        if reflection:
            reflection.reflection_text = reflection_text
            reflection.embedding = np.array(embedding) 
            reflection.importance_score = importance_score 
            reflection.reflection_type = reflection_type 
        else:
            reflection = UserReflection(
                user_id=user_id,
                reflection_text=reflection_text,
                embedding=np.array(embedding),
                importance_score=importance_score,
                reflection_type=reflection_type,
            )
            db.add(reflection)
        await db.flush()
        await db.commit()
        await db.refresh(reflection)
        return reflection

    except SQLAlchemyError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise

async def get_similar_importance_recent_reflections(db: AsyncSession, user_id: int, reflection_text: str, top_n: int = 3, similarity_weight: float = 0.4, importance_weight: float = 0.4, recency_weight: float = 0.2):  
    """
    Gets similar user reflections based on importance, similarity, and recency.
    ... (rest of the docstring)
    """
    table_name = "user_reflections"
    embedding_column = "embedding"
    return_columns = ["reflection_text", "importance_score"]

    similar_reflections = await retrieve_similar_importance_recent_messages(
        db=db,
        user_id=user_id,
        query_text=reflection_text,
        table_name=table_name,
        embedding_column_name=embedding_column,
        return_column_names=return_columns,
        top_k=top_n,
        similarity_weight=similarity_weight,
        importance_weight=importance_weight,
        recency_weight=recency_weight,
        additional_filters={"reflection_type": "Counsellor"},
    )

    return similar_reflections


async def get_user_reflections(db: AsyncSession, user_id: int, limit: int = 10) -> List[UserReflection]:  
    result = await db.execute(select(UserReflection).filter(UserReflection.user_id == user_id).order_by(desc(UserReflection.updated_at)).limit(limit))
    return result.scalars().all()


async def get_latest_user_reflection(db: AsyncSession, user_id: int) -> Optional[UserReflection]:  
    result = await db.execute(select(UserReflection).filter(UserReflection.user_id == user_id).order_by(UserReflection.updated_at.desc()))
    return result.scalars().first()


async def delete_user_reflection(db: AsyncSession, reflection_id: int) -> None:  
    result = await db.execute(select(UserReflection).filter(UserReflection.id == reflection_id))
    reflection = result.scalars().first()
    if reflection:
        await db.delete(reflection)
        await db.commit()