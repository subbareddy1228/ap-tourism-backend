"""add route columns to tracking_sessions

Revision ID: c7d8e9f0a1b2
Revises: a3f1c9e2b841
Create Date: 2026-04-10 00:00:00.000000

What this migration adds to tracking_sessions:
  - route_polyline      TEXT        NULL  — encoded polyline from Ola Maps directions
  - route_distance_km   FLOAT       NULL  — planned trip distance (fetched at session start)
  - route_duration_min  FLOAT       NULL  — planned trip duration (fetched at session start)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'c7d8e9f0a1b2'
down_revision = 'a3f1c9e2b841'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'tracking_sessions',
        sa.Column('route_polyline', sa.Text(), nullable=True),
    )
    op.add_column(
        'tracking_sessions',
        sa.Column('route_distance_km', sa.Float(), nullable=True),
    )
    op.add_column(
        'tracking_sessions',
        sa.Column('route_duration_min', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('tracking_sessions', 'route_duration_min')
    op.drop_column('tracking_sessions', 'route_distance_km')
    op.drop_column('tracking_sessions', 'route_polyline')
