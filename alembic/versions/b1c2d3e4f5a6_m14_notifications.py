"""add notification tables

Revision ID: a1b2c3d4e5f6
Revises: 0df9f7fc524c
Create Date: 2026-03-24 10:00:00.000000

M14 — Notification APIs
Creates:
    notifications              — per-user notification inbox
    notification_preferences   — per-user channel & type toggle settings

Also adds:
    users.fcm_token            — Firebase device token (nullable)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add fcm_token to users table ──────────────────────────
    # Needed by send_notification to dispatch FCM push
    op.add_column(
        'users',
        sa.Column('fcm_token', sa.String(length=255), nullable=True)
    )

    # ── notifications ──────────────────────────────────────────
    op.create_table(
        'notifications',
        sa.Column('id',             postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id',        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type',           sa.String(length=50),          nullable=False),
        sa.Column('title',          sa.String(length=200),         nullable=False),
        sa.Column('body',           sa.Text(),                     nullable=False),
        sa.Column('channel',        sa.String(length=20),          nullable=False,
                  server_default='in_app'),
        sa.Column('is_read',        sa.Boolean(),                  nullable=False,
                  server_default=sa.text('false')),
        sa.Column('data',           postgresql.JSONB(),            nullable=True),
        sa.Column('fcm_message_id', sa.String(length=200),        nullable=True),
        sa.Column('created_at',     sa.DateTime(),                 nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('read_at',        sa.DateTime(),                 nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_notifications_user_id',  'notifications', ['user_id'])
    op.create_index('ix_notifications_is_read',  'notifications', ['is_read'])
    op.create_index('ix_notifications_type',     'notifications', ['type'])
    op.create_index('ix_notifications_created',  'notifications', ['created_at'])

    # ── notification_preferences ───────────────────────────────
    op.create_table(
        'notification_preferences',
        sa.Column('id',               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id',          postgresql.UUID(as_uuid=True), nullable=False,
                  unique=True),
        sa.Column('push_enabled',     sa.Boolean(), nullable=False,
                  server_default=sa.text('true')),
        sa.Column('sms_enabled',      sa.Boolean(), nullable=False,
                  server_default=sa.text('true')),
        sa.Column('email_enabled',    sa.Boolean(), nullable=False,
                  server_default=sa.text('true')),
        sa.Column('type_preferences', postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column('updated_at',       sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(
        'ix_notification_preferences_user_id',
        'notification_preferences', ['user_id'], unique=True
    )


def downgrade() -> None:
    op.drop_index('ix_notification_preferences_user_id',
                  table_name='notification_preferences')
    op.drop_table('notification_preferences')

    op.drop_index('ix_notifications_created',  table_name='notifications')
    op.drop_index('ix_notifications_type',     table_name='notifications')
    op.drop_index('ix_notifications_is_read',  table_name='notifications')
    op.drop_index('ix_notifications_user_id',  table_name='notifications')
    op.drop_table('notifications')

    op.drop_column('users', 'fcm_token')
