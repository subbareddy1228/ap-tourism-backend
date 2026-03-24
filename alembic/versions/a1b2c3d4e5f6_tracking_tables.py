"""add tracking tables

Revision ID: a1b2c3d4e5f6
Revises: 0df9f7fc524c
Create Date: 2026-03-24 10:00:00.000000

M18 — Tracking Module
Branch : feature/LEV156-tracking
Author : LEV156 Ram Kishore Pawar
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '0df9f7fc524c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── tracking_sessions ─────────────────────────────────────
    op.create_table(
        'tracking_sessions',
        sa.Column('id',          sa.UUID(), nullable=False),
        sa.Column('booking_id',  sa.UUID(), nullable=False),
        sa.Column('user_id',     sa.UUID(), nullable=False),
        sa.Column('tracker_id',  sa.UUID(), nullable=False),
        sa.Column('tracker_role', sa.String(20), nullable=False),   # "DRIVER" | "GUIDE"
        sa.Column('status',      sa.String(20),  nullable=False, server_default='ACTIVE'),
        sa.Column('share_token',  sa.String(64),  nullable=False),
        sa.Column('share_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('trip_started_at',   sa.DateTime(timezone=True), nullable=True),
        sa.Column('trip_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_id'),
        sa.UniqueConstraint('share_token'),
    )
    op.create_index('ix_tracking_sessions_id',         'tracking_sessions', ['id'])
    op.create_index('ix_tracking_sessions_booking_id', 'tracking_sessions', ['booking_id'])
    op.create_index('ix_tracking_sessions_user_id',    'tracking_sessions', ['user_id'])
    op.create_index('ix_tracking_sessions_tracker_id', 'tracking_sessions', ['tracker_id'])
    op.create_index('ix_tracking_sessions_share_token','tracking_sessions', ['share_token'])

    # ── trip_locations (latest ping — one row per session) ────
    op.create_table(
        'trip_locations',
        sa.Column('id',         sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('latitude',   sa.Float(), nullable=False),
        sa.Column('longitude',  sa.Float(), nullable=False),
        sa.Column('accuracy',   sa.Float(), nullable=True),
        sa.Column('speed',      sa.Float(), nullable=True),
        sa.Column('bearing',    sa.Float(), nullable=True),
        sa.Column('altitude',   sa.Float(), nullable=True),
        sa.Column('address',    sa.String(500), nullable=True),
        sa.Column('destination_lat',       sa.Float(), nullable=True),
        sa.Column('destination_lng',       sa.Float(), nullable=True),
        sa.Column('eta_minutes',           sa.Float(), nullable=True),
        sa.Column('distance_remaining_km', sa.Float(), nullable=True),
        sa.Column('pinged_at',  sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['tracking_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id'),
    )
    op.create_index('ix_trip_locations_session_id', 'trip_locations', ['session_id'])

    # ── location_history (breadcrumb — append-only) ───────────
    op.create_table(
        'location_history',
        sa.Column('id',         sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('latitude',   sa.Float(), nullable=False),
        sa.Column('longitude',  sa.Float(), nullable=False),
        sa.Column('accuracy',   sa.Float(), nullable=True),
        sa.Column('speed',      sa.Float(), nullable=True),
        sa.Column('bearing',    sa.Float(), nullable=True),
        sa.Column('altitude',   sa.Float(), nullable=True),
        sa.Column('pinged_at',  sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['tracking_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_location_history_session_pinged',
        'location_history', ['session_id', 'pinged_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_location_history_session_pinged',   table_name='location_history')
    op.drop_table('location_history')

    op.drop_index('ix_trip_locations_session_id',         table_name='trip_locations')
    op.drop_table('trip_locations')

    op.drop_index('ix_tracking_sessions_share_token',     table_name='tracking_sessions')
    op.drop_index('ix_tracking_sessions_tracker_id',      table_name='tracking_sessions')
    op.drop_index('ix_tracking_sessions_user_id',         table_name='tracking_sessions')
    op.drop_index('ix_tracking_sessions_booking_id',      table_name='tracking_sessions')
    op.drop_index('ix_tracking_sessions_id',              table_name='tracking_sessions')
    op.drop_table('tracking_sessions')
