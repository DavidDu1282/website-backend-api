import os

class Settings:
    PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
    LOCATION = os.getenv("GOOGLE_REGION", "us-central1")

settings = Settings()
