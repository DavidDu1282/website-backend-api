# alembic/env.py

import sys
import os
from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from sqlalchemy.engine.url import make_url
from alembic import context
from dotenv import load_dotenv


# --- Path Handling (Corrected and Improved) ---
# 1. Find the project root reliably
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 2. Add the project root to sys.path
sys.path.insert(0, PROJECT_ROOT)

# --- Model Imports ---
from app.data.database import Base
from app.models.database_models.user import User
from app.models.database_models.tarot_reading_history import TarotReadingHistory
from app.models.database_models.counsellor_message_history import CounsellorMessageHistory
from app.models.database_models.user_reflection import UserReflection
from app.models.database_models.user_plan import UserPlan
from app.models.database_models.importance_sample_messages import ImportanceSampleMessages

from app.core.config import settings

# --- Print Metadata Tables ---
print(Base.metadata.tables)  # <--- Add this line!

# 3. Load the .env file (now with a correct path)
DOTENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(DOTENV_PATH)

# --- Alembic Configuration ---
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    parsed_url = make_url(url)  # Use make_url to parse the URL string
    dialect_name = parsed_url.drivername # Access the dialect name
    render_as_batch_setting = dialect_name == 'sqlite'
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    # database_url = os.getenv("DATABASE_URL")
    if settings.DATABASE_URL is None:
        raise ValueError("DATABASE_URL environment variable not set.")
    connectable = create_engine(settings.DATABASE_URL)
    with connectable.connect() as connection:  # Only needed for online migrations
        if connection.dialect.name == 'sqlite':  # Add this check
            render_as_batch_setting = True
        else:
            render_as_batch_setting = False

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=render_as_batch_setting,  # Use the variable
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
