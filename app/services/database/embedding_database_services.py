# app/services/database_services/embedding_database_services.py
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from pgvector.sqlalchemy import Vector  # Import the Vector type
from sqlalchemy import MetaData, Table, func, and_
from sentence_transformers import SentenceTransformer
import numpy as np

embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def generate_embedding(text: str):
    """Generate a 384-dimensional embedding for a given text message."""
    return np.array(embedding_model.encode(text, normalize_embeddings=True), dtype=np.float32)

def retrieve_similar_messages(
    db: Session,
    query_text: str,
    table_name: str,
    embedding_column_name: str,
    return_column_names: list[str],
    top_k: int = 10,
):
    """Retrieve similar messages using direct SQL query, NOT filtering by user_id."""
    try:
        # Generate embedding
        query_embedding = np.array(embedding_model.encode(query_text, normalize_embeddings=True), dtype=np.float32).tolist()

        # Format embedding for SQL (pgvector requires '[...]' format)
        embedding_str = f"'[{','.join(map(str, query_embedding))}]'::vector"

        # Modify SQL to filter by user_id
        sql_query = text(f"""
            SELECT 
                {', '.join(return_column_names)},
                ({embedding_column_name} <-> {embedding_str}) AS similarity_score
            FROM {table_name}
            ORDER BY similarity_score ASC
            LIMIT :top_k;
        """)

        # Execute query
        results = db.execute(sql_query, {"top_k": top_k}).fetchall()

        return [dict(row._mapping) for row in results]

    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def retrieve_similar_importance_recent_messages(
    db: Session,
    user_id: int,  # Add user_id filter
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
    """Retrieve messages using a direct SQL query, filtering by user_id."""
    try:
        # Generate embedding as NumPy array
        query_embedding = np.array(embedding_model.encode(query_text, normalize_embeddings=True), dtype=np.float32).tolist()

        # Format embedding for SQL (pgvector requires '[...]' format)
        embedding_str = f"'[{','.join(map(str, query_embedding))}]'::vector"

        # Modify SQL query to filter by user_id
        sql_query = text(f"""
            SELECT 
                {', '.join(return_column_names)},
                {similarity_weight} * (1 - ({embedding_column_name} <-> {embedding_str})) + 
                {importance_weight} * (importance_score / 10) +
                {recency_weight} * EXP(-EXTRACT(EPOCH FROM (NOW() - last_updated_timestamp)) / (86400 * {recency_days}))
                AS combined_score
            FROM {table_name}
            WHERE user_id = :user_id  -- Ensure only messages from this user
              AND (EXTRACT(EPOCH FROM (NOW() - last_updated_timestamp)) / 86400) <= :recency_days
            ORDER BY combined_score DESC
            LIMIT :top_k;
        """)

        # Execute query
        results = db.execute(sql_query, {
            "user_id": user_id,  # Pass user_id
            "recency_days": recency_days,
            "top_k": top_k
        }).fetchall()

        return [dict(row._mapping) for row in results]

    except Exception as e:
        print(f"An error occurred: {e}")
        return []
