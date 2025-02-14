# app/models/token.py
from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    success: bool
    access_token: str
    refresh_token: str  # Include refresh token
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None