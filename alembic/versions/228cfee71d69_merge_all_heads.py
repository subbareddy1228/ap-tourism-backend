"""merge all heads

Revision ID: 228cfee71d69
Revises: 879b92c14c55, b1c2d3e4f5a6, b2c3d4e5f6a7
Create Date: 2026-03-24 14:37:08.240173

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '228cfee71d69'
down_revision: Union[str, None] = ('879b92c14c55', 'b1c2d3e4f5a6', 'b2c3d4e5f6a7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
