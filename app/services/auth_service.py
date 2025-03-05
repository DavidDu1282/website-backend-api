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
from app.models.database_models.user import User
from app.models.token import TokenData
from app.models.password_validation import PasswordValidationError


# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login") # No longer needed

# --- In-Memory Token Blacklist (FOR DEVELOPMENT/TESTING ONLY) ---
# blacklisted_tokens = set()  # No longer needed with HTTP-only cookies


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

# No longer needed, handled by cookies now
# async def get_current_user(
#     token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
# ):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
#         username: str = payload.get("sub")
#         if username is None:
#             raise credentials_exception
#         token_data = TokenData(username=username)
#     except JWTError:
#         raise credentials_exception

#     if is_token_blacklisted(token):  # Check if token is blacklisted
#         raise credentials_exception

#     user = db.query(User).filter(User.username == token_data.username).first()
#     if user is None:
#         raise credentials_exception

#     # Return both the user and the token
#     return user, token

# No longer needed: now we get the token from a cookie
# def extract_optional_user_id(request: Request):
#     """Extract user ID from JWT token if available, otherwise return None."""
#     print("Extracting user ID from token")
#     access_token = request.cookies.get("access_token")
#     print(f"Access token: {access_token}")
#     if not access_token:
#         return None  # No token = unauthenticated user

#     try:
#         payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
#         return payload["sub"]  # Return user ID if authenticated
#     except JWTError:
#         return None  # Invalid token = treat as unauthenticated

# No longer needed, as we're using HTTP-only cookies.
# def is_token_blacklisted(token: str) -> bool:
#     """Check if a token is blacklisted (in-memory for this example)."""
#     return token in blacklisted_tokens

# def blacklist_token(token: str):
#     """Blacklist a token (in-memory for this example)."""
#     blacklisted_tokens.add(token)

def validate_password(password: str):
    """Ensure password meets security requirements."""
    errors = []
    if len(password) < 8:
        errors.append("8_characters_long")
    if not any(char.isdigit() for char in password):
        errors.append("one_digit")
    if not any(char.isupper() for char in password):
        errors.append("one_uppercase")
    if not any(char.islower() for char in password):
        errors.append("one_lowercase")
    if not any(char in "!@#$%^&*()" for char in password):
        errors.append("one_special")

    if errors:
        raise PasswordValidationError(errors)

    return True

def get_current_user_from_cookie(
    request: Request, db: Session = Depends(get_db)
):
    access_token = request.cookies.get("access_token")
    if not access_token:
        print("No access token found in cookies")
        raise HTTPException(status_code=401, detail="Missing access token")

    try:
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
        print("Decoded JWT payload:", payload)
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError as e:
        print("JWT decode error:", str(e))
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        print("User not found in database")
        raise HTTPException(status_code=401, detail="User not found")

    return user

# def get_current_user_from_cookie(
#     db: Session = Depends(get_db), access_token: str | None = None
# ) -> User:
#     """
#     Get the current user from the access token cookie.  This replaces
#     the previous get_current_user dependency.
#     """
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     if access_token is None:
#         raise credentials_exception

#     try:
#         payload = jwt.decode(
#             access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
#         )
#         username: str = payload.get("sub")
#         if username is None:
#             raise credentials_exception
#         token_data = TokenData(username=username)
#     except JWTError:
#         raise credentials_exception

#     user = db.query(User).filter(User.username == token_data.username).first()
#     if user is None:
#         raise credentials_exception
#     return user
