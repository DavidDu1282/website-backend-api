"""attempting to add Tarot_reading and User Tables

Revision ID: 4fa3554f867d
Revises: 225a70065457
Create Date: 2025-02-08 21:24:09.741276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fa3554f867d'
down_revision: Union[str, None] = '225a70065457'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
