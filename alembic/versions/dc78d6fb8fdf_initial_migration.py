"""Initial migration

Revision ID: dc78d6fb8fdf
Revises: 15d8a6a62bec
Create Date: 2025-02-08 21:07:34.507569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc78d6fb8fdf'
down_revision: Union[str, None] = '15d8a6a62bec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
