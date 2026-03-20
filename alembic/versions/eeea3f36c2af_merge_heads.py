"""merge heads

Revision ID: eeea3f36c2af
Revises: 1b97aec71e82, ed5968b8047b
Create Date: 2026-03-20 09:42:16.854645

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'eeea3f36c2af'
down_revision: Union[str, None] = ('1b97aec71e82', 'ed5968b8047b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
