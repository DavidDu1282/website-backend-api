# app/services/database/user_services.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import exists, desc
from app.models.database_models.user import User  # Import from your models
from app.models.database_models.user_prompt import UserPrompt

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

def create_user_prompt(db: Session, user_id: int, prompt_text: str, prompt_type: str) -> UserPrompt:
    new_prompt = UserPrompt(user_id=user_id, prompt_text=prompt_text, prompt_type=prompt_type)
    db.add(new_prompt)
    db.commit()
    db.refresh(new_prompt)
    return new_prompt

def get_user_prompts(db: Session, user_id: int, prompt_type: Optional[str] = None, limit: int = 10) -> List[UserPrompt]:
    query = db.query(UserPrompt).filter(UserPrompt.user_id == user_id)

    if prompt_type:
        query = query.filter(UserPrompt.prompt_type == prompt_type)

    return query.order_by(desc(UserPrompt.timestamp)).limit(limit).all()

def delete_user_prompt(db: Session, prompt_id: int) -> None:
    prompt = db.query(UserPrompt).filter(UserPrompt.id == prompt_id).first()
    if prompt:
        db.delete(prompt)
        db.commit()