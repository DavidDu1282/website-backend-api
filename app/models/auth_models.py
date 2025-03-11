# app/models/auth.py
from typing import List, Optional

from pydantic import BaseModel


class PasswordValidationError(Exception):
    def __init__(self, messages: List[str]):
        self.messages = messages
        super().__init__(", ".join(messages))


class ValidationError(BaseModel):
    loc: List[str]
    msg: str
    type: str


class ErrorResponse(BaseModel):
    detail: List[ValidationError]


class Token(BaseModel):
    success: bool
    access_token: str
    refresh_token: str  
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str