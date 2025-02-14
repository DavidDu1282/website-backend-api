"""Changing user model to store password as binary

Revision ID: bd2e4d3c697e
Revises: b4040894248b
Create Date: 2024-07-27 14:49:01.852792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd2e4d3c697e'
down_revision: Union[str, None] = 'b4040894248b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('username',
               existing_type=sa.VARCHAR(),
               nullable=True)
        batch_op.alter_column('hashed_password',
               existing_type=sa.VARCHAR(),
               type_=sa.LargeBinary(),
               existing_nullable=False)  # Corrected: Use LargeBinary


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('hashed_password',
               existing_type=sa.LargeBinary(),
               type_=sa.VARCHAR(),
               existing_nullable=False)
        batch_op.alter_column('username',
               existing_type=sa.VARCHAR(),
               nullable=False)