# app/services/auth_service.py
import re
from datetime import datetime, timedelta
from typing import Optional

import bcrypt  # Import the bcrypt library directly
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.data.database import get_db
from app.models.user import User
from app.models.token import TokenData


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- In-Memory Token Blacklist (FOR DEVELOPMENT/TESTING ONLY) ---
blacklisted_tokens = set()


def verify_password(plain_password, hashed_password):
    # bcrypt requires bytes, not strings.  Crucially, we encode the plain
    # password using UTF-8 *before* hashing, and compare against the stored
    # hashed password (which is already bytes).
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password)


def hash_password(password):
    # Generate a salt and hash the password (bcrypt handles salt generation)
    # The result is a byte string.  We return this byte string directly.
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


async def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )  # Use the same secret key and algorithm
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    if is_token_blacklisted(token):  # Check if token is blacklisted
        raise credentials_exception

    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception

    # Return both the user and the token
    return user, token


def extract_optional_user_id(request: Request):
    """Extract user ID from JWT token if available, otherwise return None."""
    print("Extracting user ID from token")
    access_token = request.cookies.get("access_token")
    print(access_token)
    if not access_token:
        return None  # No token = unauthenticated user

    try:
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]  # Return user ID if authenticated
    except JWTError:
        return None  # Invalid token = treat as unauthenticated


def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted (in-memory for this example)."""
    return token in blacklisted_tokens


def blacklist_token(token: str):
    """Blacklist a token (in-memory for this example)."""
    blacklisted_tokens.add(token)


def validate_password(password: str):
    """Ensure password meets security requirements."""
    if len(password) < 12:
        raise HTTPException(
            status_code=400, detail="Password must be at least 12 characters long."
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=400, detail="Password must include at least one number."
        )
    if not re.search(r"[A-Za-z]", password):
        raise HTTPException(
            status_code=400, detail="Password must include at least one letter."
        )
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must include at least one special character.",
        )
    return password
