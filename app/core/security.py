from slowapi import Limiter
from slowapi.util import get_remote_address
import secrets

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)

# CSRF Token Management
csrf_tokens = {}

def generate_csrf_token():
    token = secrets.token_urlsafe(32)
    csrf_tokens[token] = True
    return token

def validate_csrf_token(token):
    if token not in csrf_tokens:
        return False
    del csrf_tokens[token]  # One-time use
    return True
