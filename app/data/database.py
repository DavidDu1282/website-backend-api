# d:\OtherCodingProjects\website-backend-api\app\data\database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Moves up to project root
DOTENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(DOTENV_PATH)

# Read database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Configure engine based on database type
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)  # PostgreSQL or other databases

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Only ONE declarative_base() call!
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()