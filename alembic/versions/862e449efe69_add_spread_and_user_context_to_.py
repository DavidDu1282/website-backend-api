"""Add spread and user_context to TarotReadingHistory, change interpretation and user_context to Text

Revision ID: 862e449efe69
Revises: e3b7aac21bda
Create Date: 2025-03-02 10:23:32.861030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '862e449efe69'
down_revision: Union[str, None] = 'e3b7aac21bda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
