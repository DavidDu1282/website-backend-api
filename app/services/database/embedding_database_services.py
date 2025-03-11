# app/services/database_services/embedding_database_services.py
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.sql import cast
from pgvector.sqlalchemy import Vector  # Import the Vector type
from sqlalchemy import MetaData, Table, func, and_
from sentence_transformers import SentenceTransformer
import numpy as np

embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def generate_embedding(text: str):
    """Generate a 384-dimensional embedding for a given text message."""
    return np.array(embedding_model.encode(text, normalize_embeddings=True), dtype=np.float32)

# def format_pgvector(embedding):
#     """Convert a Python list to PostgreSQL vector format."""
#     return f"'[{','.join(map(str, embedding))}]'::vector"

from sqlalchemy.sql import text
import numpy as np

from sqlalchemy.sql import text
import numpy as np

def retrieve_similar_messages(
    db: Session,
    query_text: str,
    table_name: str,
    embedding_column_name: str,
    return_column_names: list[str],
    top_k: int = 10,
):
    """Retrieve similar messages using direct SQL query."""
    try:
        # Generate embedding as NumPy array, then convert to list
        query_embedding = np.array(embedding_model.encode(query_text, normalize_embeddings=True), dtype=np.float32).tolist()

        # Format embedding for SQL (PostgreSQL requires '[...]' format for vectors)
        embedding_str = f"'[{','.join(map(str, query_embedding))}]'::vector"

        # Build the SQL query (REMOVED `1 -` TO FIX INTEGER MISMATCH)
        sql_query = text(f"""
            SELECT 
                {', '.join(return_column_names)},
                ({embedding_column_name} <-> {embedding_str}) AS similarity_score
            FROM {table_name}
            ORDER BY similarity_score ASC  -- Lower is better for cosine distance
            LIMIT :top_k;
        """)

        # Execute the query
        results = db.execute(sql_query, {"top_k": top_k}).fetchall()
        print(results)

        # Convert results to a list of dictionaries
        return [dict(row._mapping) for row in results]

    except Exception as e:
        print(f"An error occurred: {e}")
        return []



from sqlalchemy.sql import text
import numpy as np

def retrieve_similar_importance_recent_messages(
    db: Session,
    query_text: str,
    table_name: str,
    embedding_column_name: str,
    return_column_names: List[str],
    top_k: int = 10,
    recency_days: int = 30,
    similarity_weight: float = 0.4,
    importance_weight: float = 0.4,
    recency_weight: float = 0.2,
):
    """Retrieve messages using a direct SQL query."""
    try:
        # Generate embedding as NumPy array, then convert to list
        query_embedding = np.array(embedding_model.encode(query_text, normalize_embeddings=True), dtype=np.float32).tolist()

        # # Format embedding for SQL (PostgreSQL uses '[...]' format for vectors)
        embedding_str = f"'[{','.join(map(str, query_embedding))}]'::vector"

        sql_query = text(f"""
            SELECT 
                {', '.join(return_column_names)},
                {similarity_weight} * (1 - ({embedding_column_name} <-> {embedding_str})) + 
                {importance_weight} * (importance_score / 10) +
                {recency_weight} * EXP(-EXTRACT(EPOCH FROM (NOW() - last_updated_timestamp)) / (86400 * {recency_days}))
                AS combined_score
            FROM {table_name}
            ORDER BY combined_score DESC
            LIMIT :top_k;
        """)

        # Execute query
        results = db.execute(sql_query, {
            "top_k": top_k
        }).fetchall()

        print(results)

        # Convert results to a list of dictionaries
        return [dict(row._mapping) for row in results]

    except Exception as e:
        print(f"An error occurred: {e}")
        return []
