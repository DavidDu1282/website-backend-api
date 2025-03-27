# app/services/auth_service.py
import re
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.data.database import get_db
from app.models.database_models.user import User

from app.models.auth_models import PasswordValidationError, TokenData


def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password)


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


async def authenticate_user(db: AsyncSession, username: str, password: str):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
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
    to_encode.update({"exp": expire, "type": "access"}) 
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
    to_encode.update({"exp": expire, "type": "refresh"})  
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def validate_password(password: str):
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


async def get_current_user_from_cookie(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    if access_token:
        try:
            payload = jwt.decode(
                access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            if payload.get("type") != "access":
                raise JWTError("Invalid token type")
            username: str = payload.get("sub")
            if not username:
                raise JWTError("Invalid token payload")
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalars().first()
            if not user:
                raise JWTError("User not found")
            return user
        except JWTError as e:
            print(f"Access token error: {e}")
            # Access token is invalid, try refresh token
            pass

    if refresh_token:
        try:
            payload = jwt.decode(
                refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            if payload.get("type") != "refresh":
                raise JWTError("Invalid token type")
            username: str = payload.get("sub")
            if not username:
                raise JWTError("Invalid token payload")

            result = await db.execute(select(User).where(User.username == username))
            user = result.scalars().first()
            if not user:
                raise JWTError("User not found")

            new_access_token = create_access_token(data={"sub": username})
            new_refresh_token = create_refresh_token(data={"sub": username})

            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                secure=True,
                samesite="lax",
                expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=True,
                secure=True,
                samesite="lax",
                expires=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            )

            return user

        except JWTError as e:
            print(f"Refresh token error: {e}")
            # Both tokens are invalid/expired
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

    # No valid tokens found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

