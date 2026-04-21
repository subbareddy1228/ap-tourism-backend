"""add timestamps to darshan_bookings

Revision ID: 365dbb468805
Revises: 93402bd1e2c5
Create Date: 2026-04-15 17:50:24.393612

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '365dbb468805'
down_revision: Union[str, None] = '93402bd1e2c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('darshan_bookings', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('darshan_bookings', sa.Column('updated_at', sa.DateTime(), nullable=True))



def downgrade() -> None:
    op.drop_column('darshan_bookings', 'updated_at')
    op.drop_column('darshan_bookings', 'created_at')
