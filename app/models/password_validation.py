# app/models/password_validation.py
from typing import List

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