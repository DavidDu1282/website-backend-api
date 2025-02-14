"""attempting to add Tarot_reading and User Tables

Revision ID: 157a9afbfb32
Revises: dc78d6fb8fdf
Create Date: 2025-02-08 21:14:29.313267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '157a9afbfb32'
down_revision: Union[str, None] = 'dc78d6fb8fdf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
