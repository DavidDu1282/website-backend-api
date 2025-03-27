#%%
import json
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.database import Base
from core.config import settings

load_dotenv()

db_url = settings.DATABASE_URL

def load_few_shot_data(filepath: str) -> list:
    """Load sample data from a JSON file."""
    with open(filepath, 'r', encoding="utf-8") as f:
        return json.load(f)

def create_embeddings_and_store(filepath: str, db_url: str):
    """Loads data, creates embeddings, and stores them in the database while avoiding duplicates."""

    examples = load_few_shot_data(filepath)

    model = SentenceTransformer('all-MiniLM-L6-v2')

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    session = Session(engine)

    try:
        values_to_insert = []
        for ex in examples:
            text_content = ex["text"]
            label = ex["label"]

            embedding = model.encode(text_content, convert_to_tensor=False).tolist()

            values_to_insert.append({
                "sample_message": text_content,
                "importance_score": label,
                "embedding": embedding
            })

        if values_to_insert:
            insert_query = text("""
                INSERT INTO importance_sample_messages (sample_message, importance_score, embedding)
                VALUES (:sample_message, :importance_score, :embedding)
                ON CONFLICT (sample_message) DO NOTHING;
            """)

            for entry in values_to_insert:
                session.execute(insert_query, entry)

            session.commit()
            print(f"Successfully stored {len(values_to_insert)} new embeddings in the database.")
        else:
            print("No new embeddings to store.")

    except IntegrityError as ie:
        session.rollback()
        print(f"Integrity Error: {ie}")
    except Exception as e:
        session.rollback()
        print(f"Unexpected error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    filepath = r"d:\OtherCodingProjects\website-backend-api\app\data\synthetic_importance_data.json"
    create_embeddings_and_store(filepath, db_url)

#%%