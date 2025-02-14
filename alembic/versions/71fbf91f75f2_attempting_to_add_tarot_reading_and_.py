"""attempting to add Tarot_reading and User Tables

Revision ID: 71fbf91f75f2
Revises: 157a9afbfb32
Create Date: 2025-02-08 21:16:27.536370

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71fbf91f75f2'
down_revision: Union[str, None] = '157a9afbfb32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
