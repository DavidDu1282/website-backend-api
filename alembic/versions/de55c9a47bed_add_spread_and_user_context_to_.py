"""Add spread and user_context to TarotReadingHistory, change interpretation and user_context to Text

Revision ID: de55c9a47bed
Revises: 862e449efe69
Create Date: 2025-03-02 10:42:36.473180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de55c9a47bed'
down_revision: Union[str, None] = '862e449efe69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
