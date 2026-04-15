"""merge heads

Revision ID: fc2c00c13f3c
Revises: 7e220c9e88d7, c7d8e9f0a1b2
Create Date: 2026-04-14 16:04:10.849687

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'fc2c00c13f3c'
down_revision: Union[str, None] = ('7e220c9e88d7', 'c7d8e9f0a1b2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
