# app/core/config.py
from pydantic_settings import BaseSettings  # Corrected import
import os

class Settings(BaseSettings):
    SECRET_KEY: str  # !!! CHANGE THIS TO A STRONG, RANDOM SECRET !!!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "" 

    SERVER_IP: str = "0.0.0.0" 

    GOOGLE_PROJECT_ID: str
    GOOGLE_REGION: str
    class Config:
        env_file = ".env"
        extra = "allow"  # This ensures extra env variables won't break validation


settings = Settings()
print(f"Loaded SERVER_IP: {settings.SERVER_IP}")

settings.REDIS_URL = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"

# Explicitly set the environment variables for Vertex AI
# os.environ["GOOGLE_PROJECT_ID"] = settings.GOOGLE_PROJECT_ID
# os.environ["GOOGLE_REGION"] = settings.GOOGLE_REGION
# print(f"Loaded GOOGLE_PROJECT_ID: {os.environ['GOOGLE_PROJECT_ID']}")
# print(f"Loaded GOOGLE_REGION: {os.environ['GOOGLE_REGION']}")