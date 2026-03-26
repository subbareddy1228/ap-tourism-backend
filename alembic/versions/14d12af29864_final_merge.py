"""final_merge

Revision ID: 14d12af29864
Revises: 0a9b5f4b434f
Create Date: 2026-03-26 18:28:11.208470

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '14d12af29864'
down_revision: Union[str, None] = '0a9b5f4b434f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
