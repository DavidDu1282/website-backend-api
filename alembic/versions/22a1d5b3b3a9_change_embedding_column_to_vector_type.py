"""Change embedding column to vector type

Revision ID: 22a1d5b3b3a9
Revises: 2f7ca677dd01
Create Date: 2025-03-08 11:43:40.131096

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  # Import Vector here

# revision identifiers, used by Alembic.
revision = '22a1d5b3b3a9'  # Replace with the generated ID
down_revision = '2f7ca677dd01' # Replace
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Counsellor Message History ---
    op.alter_column('counsellor_message_history', 'embedding',
                    existing_type=sa.ARRAY(sa.FLOAT()),  # Old type
                    type_=Vector(384),                   # New type
                    postgresql_using='embedding::text::vector(384)',
                    existing_nullable=True)

    # --- Importance Sample Messages ---
    op.alter_column('importance_sample_messages', 'embedding',
                    existing_type=sa.ARRAY(sa.FLOAT()),  # Old type
                    type_=Vector(384),                   # New type
                    postgresql_using='embedding::text::vector(384)',
                    existing_nullable=True)
    #Create Index
    op.execute("CREATE INDEX IF NOT EXISTS counsellor_message_history_embedding_idx ON counsellor_message_history USING hnsw (embedding vector_l2_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS importance_sample_messages_embedding_idx ON importance_sample_messages USING hnsw (embedding vector_l2_ops)")

def downgrade() -> None:
    # --- Counsellor Message History ---
    op.alter_column('counsellor_message_history', 'embedding',
                    existing_type=Vector(384),           # Old type
                    type_=sa.ARRAY(sa.FLOAT()),          # New type
                    existing_nullable=True)

    # --- Importance Sample Messages ---
    op.alter_column('importance_sample_messages', 'embedding',
                    existing_type=Vector(384),          # Old type
                    type_=sa.ARRAY(sa.FLOAT()),         # New type
                    existing_nullable=True)
    #Drop Index
    op.execute("DROP INDEX IF EXISTS counsellor_message_history_embedding_idx")
    op.execute("DROP INDEX IF EXISTS importance_sample_messages_embedding_idx")
