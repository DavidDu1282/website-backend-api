# app/services/database/user_database_services.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import exists, desc, func
from app.models.database_models.user import User  # Import from your models
from app.models.database_models.user_plan import UserPlan
from app.models.database_models.user_reflection import UserReflection
from app.services.database.embedding_database_services import generate_embedding, retrieve_similar_importance_recent_messages  # Import
from app.services.database.importance_database_services import calculate_overall_importance  # Import
import numpy as np
from sqlalchemy.exc import SQLAlchemyError


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, username: str, email: str, hashed_password: str) -> User:
    if db.query(exists().where(User.username == username)).scalar():
        raise ValueError("Username already taken")
    if db.query(exists().where(User.email == email)).scalar():
        raise ValueError("Email already registered")

    db_user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def delete_user(db: Session, user_id: int) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()


# --- User Plan Functions ---

def create_user_plan(db: Session, user_id: int, plan_text: str, plan_type: Optional[str] = None) -> UserPlan:
    # Deactivate other plans
    db.query(UserPlan).filter(UserPlan.user_id == user_id).update({UserPlan.active_plan: False})

    new_plan = UserPlan(user_id=user_id, plan_text=plan_text, plan_type=plan_type, active_plan=True)
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    return new_plan


def get_user_plans(db: Session, user_id: int, plan_type: Optional[str] = None, limit: int = 10, active_only: bool = False) -> List[UserPlan]:
    query = db.query(UserPlan).filter(UserPlan.user_id == user_id)

    if plan_type:
        query = query.filter(UserPlan.plan_type == plan_type)
    if active_only:
        query = query.filter(UserPlan.active_plan == True)

    return query.order_by(desc(UserPlan.created_at)).limit(limit).all()


def get_active_user_plan(db: Session, user_id: int) -> Optional[UserPlan]:
    return db.query(UserPlan).filter(UserPlan.user_id == user_id, UserPlan.active_plan == True).first()

def delete_user_plan(db: Session, plan_id: int) -> None:
    plan = db.query(UserPlan).filter(UserPlan.id == plan_id).first()
    if plan:
        db.delete(plan)
        db.commit()


def update_user_plan(db: Session, plan_id: int, plan_text: str, plan_type: Optional[str] = None, active:Optional[bool] = None) -> UserPlan:
    plan = db.query(UserPlan).filter(UserPlan.id == plan_id).first()
    if not plan:
        raise ValueError(f"Plan with id {plan_id} not found")

    plan.plan_text = plan_text
    if plan_type is not None:
        plan.plan_type = plan_type

    if active is not None:
        if active:
            #Deactivate any other plans before activating this one
            db.query(UserPlan).filter(UserPlan.user_id == plan.user_id).update({UserPlan.active_plan:False})
        plan.active_plan = active

    db.commit()
    db.refresh(plan)
    return plan

# --- User Reflection Functions ---

def create_or_update_user_reflection(db: Session, user_id: int, reflection_text: str, reflection_type: str = "Counsellor", similarity_threshold: float = 0.6, top_k: int = 10, placeholder_value:float=0.0) -> UserReflection:
    """Creates or updates a user reflection, calculating and storing importance."""
    try:
        embedding = generate_embedding(reflection_text)
        importance_score = calculate_overall_importance(db, reflection_text, similarity_threshold, top_k, placeholder_value)

        reflection = db.query(UserReflection).filter(UserReflection.user_id == user_id).order_by(UserReflection.updated_at.desc()).first()

        if reflection:
            # Update existing
            reflection.reflection_text = reflection_text
            reflection.embedding = np.array(embedding)
            reflection.importance_score = importance_score
            reflection.reflection_type = reflection_type
        else:
            # Create new
            reflection = UserReflection(
                user_id=user_id,
                reflection_text=reflection_text,
                embedding=np.array(embedding),
                importance_score=importance_score,
                reflection_type=reflection_type,
            )
            db.add(reflection)
        db.flush() # Important!
        db.commit()
        db.refresh(reflection)
        return reflection

    except SQLAlchemyError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

def get_similar_importance_recent_reflections(db: Session, user_id: int, reflection_text: str, top_n: int = 3, similarity_weight: float = 0.4, importance_weight: float = 0.4, recency_weight: float = 0.2):
    """
    Gets similar user reflections based on importance, similarity, and recency.

    Args:
        db: The database session.
        user_id: The ID of the user.
        reflection_text: The text of the reflection to find similar reflections for.
        top_n: The maximum number of similar reflections to return.
        recency_days:  Considers reflections within the last `recency_days`.
        similarity_weight: Weight for similarity (0.0 to 1.0).
        importance_weight: Weight for importance (0.0 to 1.0).
        recency_weight: Weight for recency (0.0 to 1.0).

    Returns:
        A list of dictionaries, each containing the 'reflection_text' and 'importance_score' of a similar reflection.
    """
    table_name = "user_reflections"  # Correct table name
    embedding_column = "embedding"
    return_columns = ["reflection_text", "importance_score"] # Correct column names

    similar_reflections = retrieve_similar_importance_recent_messages(
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


def get_user_reflections(db: Session, user_id: int, limit: int = 10) -> List[UserReflection]:
    return db.query(UserReflection).filter(UserReflection.user_id == user_id).order_by(desc(UserReflection.updated_at)).limit(limit).all()


def get_latest_user_reflection(db: Session, user_id: int) -> Optional[UserReflection]:
    return db.query(UserReflection).filter(UserReflection.user_id == user_id).order_by(UserReflection.updated_at.desc()).first()


def delete_user_reflection(db: Session, reflection_id: int) -> None:
    reflection = db.query(UserReflection).filter(UserReflection.id == reflection_id).first()
    if reflection:
        db.delete(reflection)
        db.commit()