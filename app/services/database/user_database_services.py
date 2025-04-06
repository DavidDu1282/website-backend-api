# app/services/database/user_database_services.py
from typing import List, Optional

import numpy as np
from sqlalchemy import desc, exists, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models.user import User
from app.models.database_models.user_plan import UserPlan
from app.models.database_models.user_reflection import UserReflection
from app.services.database.embedding_database_services import (
    generate_embedding,
    retrieve_similar_importance_recent_messages,
)
from app.services.database.importance_database_services import (
    calculate_overall_importance,
)

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def create_user(db: AsyncSession, username: str, email: str, hashed_password: str) -> User:
    result = await db.execute(select(exists().where(User.username == username)))
    if result.scalar():
        raise ValueError("Username already taken")
    result = await db.execute(select(exists().where(User.email == email)))
    if result.scalar():
        raise ValueError("Email already registered")

    db_user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


async def delete_user(db: AsyncSession, user_id: int) -> None:
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if user:
        await db.delete(user)
        await db.commit()


async def create_user_plan(db: AsyncSession, user_id: int, plan_text: str, plan_type: Optional[str] = None) -> UserPlan:  
    await db.execute(
        UserPlan.__table__.update().where(UserPlan.user_id == user_id).values({UserPlan.active_plan: False})
    )

    new_plan = UserPlan(user_id=user_id, plan_text=plan_text, plan_type=plan_type, active_plan=True)
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)
    return new_plan


async def get_user_plans(db: AsyncSession, user_id: int, plan_type: Optional[str] = None, limit: int = 10, active_only: bool = False) -> List[UserPlan]:  
    query = select(UserPlan).filter(UserPlan.user_id == user_id)

    if plan_type:
        query = query.filter(UserPlan.plan_type == plan_type)
    if active_only:
        query = query.filter(UserPlan.active_plan == True)

    result = await db.execute(query.order_by(desc(UserPlan.created_at)).limit(limit))
    return result.scalars().all()


async def get_active_user_plan(db: AsyncSession, user_id: int) -> Optional[UserPlan]:  
    result = await db.execute(select(UserPlan).filter(UserPlan.user_id == user_id, UserPlan.active_plan == True))
    return result.scalars().first()

async def delete_user_plan(db: AsyncSession, plan_id: int) -> None: 
    result = await db.execute(select(UserPlan).filter(UserPlan.id == plan_id))
    plan = result.scalars().first()
    if plan:
        await db.delete(plan)
        await db.commit()


async def update_user_plan(db: AsyncSession, plan_id: int, plan_text: str, plan_type: Optional[str] = None, active:Optional[bool] = None) -> UserPlan:  
    result = await db.execute(select(UserPlan).filter(UserPlan.id == plan_id))
    plan = result.scalars().first()
    if not plan:
        raise ValueError(f"Plan with id {plan_id} not found")

    plan.plan_text = plan_text  
    if plan_type is not None:
        plan.plan_type = plan_type 

    if active is not None:
        if active:
             await db.execute(
                UserPlan.__table__.update().where(UserPlan.user_id == plan.user_id).values({UserPlan.active_plan: False})
            )
        plan.active_plan = active 

    await db.commit()
    await db.refresh(plan)
    return plan

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