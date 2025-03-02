# app/api/routes/auth.py
from datetime import timedelta, datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.data.database import get_db
from app.models.user import User
from app.models.token import Token, TokenData  # Keep TokenData for type hints
from app.models.password_validation import (
    PasswordValidationError,
    ValidationError,
    ErrorResponse,
)
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user_from_cookie,
    hash_password,
    validate_password,
)
from email_validator import EmailNotValidError, validate_email

router = APIRouter(tags=["Authentication"])

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

@router.post("/login")  # Removed response_model=Token
async def login(
    login_data: LoginRequest, response: Response, db: Session = Depends(get_db)
):
    """Login a user and set access and refresh tokens as HTTP-only cookies."""
    user = await authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}, expires_delta=refresh_token_expires
    )

    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  #  HTTPS only
        samesite="lax",  # Or "strict" depending on your needs
        expires=int(access_token_expires.total_seconds()),
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  #  HTTPS only
        samesite="lax",
        expires=int(refresh_token_expires.total_seconds()),
        path="/"
    )
    
    return {"success": True, "message": "Logged in successfully"}

@router.post("/logout")
async def logout(response: Response):
    """Logout a user (delete the cookies)."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Successfully logged out", "success": True}


@router.get("/check-auth")
async def check_auth(user: User = Depends(get_current_user_from_cookie)):
    """Check if the user is authenticated."""
    return {"username": user.username, "email": user.email, "success": True}

from fastapi import Cookie

@router.post("/refresh")
async def refresh_token_route(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """
    Refreshes the access token using the refresh token (provided as a cookie).
    Sets a new access token cookie.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
    )
    if refresh_token is None:
        raise credentials_exception

    try:
        payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception

    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Set new access token cookie
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        expires=int(access_token_expires.total_seconds()),
        path="/"
    )

    return {"success": True, "message": "Access token refreshed"}
