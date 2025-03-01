# app/api/routes/auth.py
from datetime import timedelta, datetime
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import settings
from app.data.database import get_db
from app.models.user import User
from app.models.token import Token, TokenData
from app.models.password_validation import PasswordValidationError, ValidationError, ErrorResponse
from app.services.auth_service import (
    authenticate_user,
    blacklist_token,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    is_token_blacklisted,
    verify_password,
    validate_password
)
from email_validator import EmailNotValidError, validate_email

router = APIRouter(tags=["Authentication"])
# --- In-Memory Rate Limiting (FOR DEVELOPMENT/TESTING ONLY) ---
in_memory_storage: Dict[str, Dict] = {}  # Global in-memory store
# Pydantic Models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):  # Added LoginRequest
    username: str
    password: str

from fastapi import Request

@router.post("/register", dependencies=[Depends(RateLimiter(times=2, seconds=5))])
async def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Register a new user."""
    
    print("Received Host Header:", request.headers.get("host"))
    print("Received Origin Header:", request.headers.get("origin"))

    # Not Validating Passwords Yet
    
    # try:
    #     validate_password(user_data.password)
    # except PasswordValidationError as e:
    #     errors = []
    #     for error_message in e.messages:
    #         errors.append(ValidationError(loc=["password"], msg=error_message, type= "value_error.password"))
    #     raise HTTPException(
    #         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #         detail=[error.model_dump() for error in errors]
    #     )
    try:
        validate_email(user_data.email)
    except EmailNotValidError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_by_username = db.query(User).filter(User.username == user_data.username).first()
    if user_by_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        )
    user_by_email = db.query(User).filter(User.email == user_data.email).first()
    if user_by_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    hashed_password = hash_password(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"success": True, "message": "User registered successfully", "user_id": user.id}

@router.post("/login", response_model=Token, dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):  # Use LoginRequest
    """Login a user and return access and refresh tokens."""
    print(login_data)
    user = await authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}, expires_delta=refresh_token_expires
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "success":True} #Return success: True


# app/api/routes/auth.py
@router.post("/logout")
async def logout(user_token: tuple[User, str] = Depends(get_current_user)): #Added User, Str type hint
    """Logout a user (blacklist the current token)."""
    current_user, token = user_token #unpack user and token
    if not is_token_blacklisted(token):
        blacklist_token(token)
    return {"message": "Successfully logged out", "success":True}

@router.get("/check-auth")
async def check_auth(user_token: tuple[User, str] = Depends(get_current_user)):
    """Check if the user is authenticated."""
    current_user, _ = user_token  # Unpack, but we don't need the token here (using _)
    return {"username": current_user.username, "email": current_user.email, "success":True}