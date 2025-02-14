"""attempting to add Tarot_reading and User Tables

Revision ID: 225a70065457
Revises: 71fbf91f75f2
Create Date: 2025-02-08 21:19:27.601396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '225a70065457'
down_revision: Union[str, None] = '71fbf91f75f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
