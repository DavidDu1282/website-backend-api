# app/core/config.py
from pydantic_settings import BaseSettings  # Corrected import


class Settings(BaseSettings):
    SECRET_KEY: str = "your-secret-key-here"  # !!! CHANGE THIS TO A STRONG, RANDOM SECRET !!!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database URL (example for SQLite)
    DATABASE_URL: str = "sqlite:///./test.db"

    class Config:
        env_file = ".env"  # Load from .env file (optional, but good practice)


settings = Settings()