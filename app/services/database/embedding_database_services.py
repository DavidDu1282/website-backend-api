# app/services/database_services/embedding_database_services.py
from typing import Any, Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import MetaData, Table, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from pgvector.sqlalchemy import Vector

embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

async def generate_embedding(text: str):
    """Generate a 384-dimensional embedding for a given text message."""
    return np.array(embedding_model.encode(text, normalize_embeddings=True), dtype=np.float32)

async def retrieve_similar_messages(
    db: AsyncSession,
    query_text: str,
    table_name: str,
    embedding_column_name: str,
    return_column_names: list[str],
    top_k: int = 10,
):
    """Retrieve similar messages using direct SQL query, NOT filtering by user_id."""
    try:
        query_embedding = np.array(embedding_model.encode(query_text, normalize_embeddings=True), dtype=np.float32).tolist()

        embedding_str = f"'[{','.join(map(str, query_embedding))}]'::vector"

        sql_query = text(f"""
            SELECT 
                {', '.join(return_column_names)},
                ({embedding_column_name} <-> {embedding_str}) AS similarity_score
            FROM {table_name}
            ORDER BY similarity_score ASC
            LIMIT :top_k;
        """)
        # sql_query = text(f"SELECT 1 FROM importance_sample_messages LIMIT 1;")

        results = await db.execute(sql_query, {"top_k": top_k})
        all_results = results.fetchall()
        return [dict(row._mapping) for row in all_results]

    except Exception as e:
        print(f"An error occurred: {e}")
        return []


async def retrieve_similar_importance_recent_messages(
    db: AsyncSession,
    user_id: int,
    query_text: str,
    table_name: str,
    embedding_column_name: str,
    return_column_names: List[str],
    top_k: int = 10,
    recency_days: int = 90,
    similarity_weight: float = 0.4,
    importance_weight: float = 0.4,
    recency_weight: float = 0.2,
    additional_filters: Optional[Dict[str, Any]] = None,
):
    """
    Retrieve messages using a direct SQL query, filtering by user_id and
    allowing for additional flexible filters.

    Args:
        db: The database session.
        user_id: The ID of the user.
        query_text: The text to find similar messages for.
        table_name: The name of the table to query.
        embedding_column_name: The name of the embedding column.
        return_column_names: A list of column names to return.
        top_k: The maximum number of messages to return.
        recency_days:  Considers messages within the last `recency_days`.
        similarity_weight: Weight for similarity.
        importance_weight: Weight for importance.
        recency_weight: Weight for recency.
        additional_filters: A dictionary of additional filters to apply.
            Keys are column names, and values are the values to filter by.
            Example:  {'reflection_type': 'counsellor'}

    Returns:
        A list of dictionaries, each representing a row from the query result.
    """
    try:
        query_embedding = np.array(
            embedding_model.encode(query_text, normalize_embeddings=True), dtype=np.float32
        ).tolist()
        embedding_str = f"'[{','.join(map(str, query_embedding))}]'::vector"

        where_clauses = ["user_id = :user_id"]
        params = {"user_id": user_id, "top_k": top_k, "recency_days": recency_days}

        if additional_filters:
            for column, value in additional_filters.items():
                where_clauses.append(f"{column} = :{column}")
                params[column] = value

        where_clause = " AND ".join(where_clauses)

        sql_query = text(
            f"""
            SELECT 
                {', '.join(return_column_names)},
                {similarity_weight} * (1 - ({embedding_column_name} <-> {embedding_str})) + 
                {importance_weight} * (importance_score / 10) +
                {recency_weight} * EXP(-EXTRACT(EPOCH FROM (NOW() - last_updated_timestamp)) / (86400 * :recency_days))
                AS combined_score
            FROM {table_name}
            WHERE {where_clause}
            ORDER BY combined_score DESC
            LIMIT :top_k;
        """
        )

        results = await db.execute(sql_query, params)
        all_results = results.fetchall()
        return [dict(row._mapping) for row in all_results]

    except Exception as e:
        print(f"An error occurred: {e}")
        return []