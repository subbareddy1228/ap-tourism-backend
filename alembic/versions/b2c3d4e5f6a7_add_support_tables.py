"""add support tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-24 11:00:00.000000

M17 — Support APIs
Creates:
    support_tickets   — customer support tickets
    ticket_messages   — threaded messages on each ticket
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── support_tickets ────────────────────────────────────────
    op.create_table(
        'support_tickets',
        sa.Column('id',            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id',       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_number', sa.String(length=30),          nullable=False),
        sa.Column('category',      sa.String(length=50),          nullable=False),
        sa.Column('subject',       sa.String(length=200),         nullable=False),
        sa.Column('priority',      sa.String(length=20),          nullable=False,
                  server_default='medium'),
        sa.Column('status',        sa.String(length=30),          nullable=False,
                  server_default='open'),
        sa.Column('booking_id',    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_to',   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at',    sa.DateTime(),                 nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at',    sa.DateTime(),                 nullable=True),
        sa.Column('resolved_at',   sa.DateTime(),                 nullable=True),
        sa.Column('closed_at',     sa.DateTime(),                 nullable=True),
        sa.Column('meta',          postgresql.JSONB(),            nullable=True),
        sa.ForeignKeyConstraint(['user_id'],     ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('ticket_number', name='uq_support_tickets_ticket_number'),
    )
    op.create_index('ix_support_tickets_user_id',        'support_tickets', ['user_id'])
    op.create_index('ix_support_tickets_ticket_number',  'support_tickets', ['ticket_number'])
    op.create_index('ix_support_tickets_booking_id',     'support_tickets', ['booking_id'])
    op.create_index('ix_support_tickets_assigned_to',    'support_tickets', ['assigned_to'])
    op.create_index('ix_support_tickets_user_status',    'support_tickets', ['user_id', 'status'])
    op.create_index('ix_support_tickets_status_priority','support_tickets', ['status', 'priority'])

    # ── ticket_messages ────────────────────────────────────────
    op.create_table(
        'ticket_messages',
        sa.Column('id',          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticket_id',   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id',   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_type', sa.String(length=20),          nullable=False,
                  server_default='user'),
        sa.Column('body',        sa.Text(),                     nullable=False),
        sa.Column('attachments', postgresql.JSONB(),            nullable=True),
        sa.Column('is_internal', sa.Boolean(),                  nullable=False,
                  server_default=sa.text('false')),
        sa.Column('created_at',  sa.DateTime(),                 nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['ticket_id'], ['support_tickets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'],           ondelete='CASCADE'),
    )
    op.create_index('ix_ticket_messages_ticket_id',   'ticket_messages', ['ticket_id'])
    op.create_index('ix_ticket_messages_sender_id',   'ticket_messages', ['sender_id'])
    op.create_index('ix_ticket_messages_created_at',  'ticket_messages', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_ticket_messages_created_at',   table_name='ticket_messages')
    op.drop_index('ix_ticket_messages_sender_id',    table_name='ticket_messages')
    op.drop_index('ix_ticket_messages_ticket_id',    table_name='ticket_messages')
    op.drop_table('ticket_messages')

    op.drop_index('ix_support_tickets_status_priority', table_name='support_tickets')
    op.drop_index('ix_support_tickets_user_status',     table_name='support_tickets')
    op.drop_index('ix_support_tickets_assigned_to',     table_name='support_tickets')
    op.drop_index('ix_support_tickets_booking_id',      table_name='support_tickets')
    op.drop_index('ix_support_tickets_ticket_number',   table_name='support_tickets')
    op.drop_index('ix_support_tickets_user_id',         table_name='support_tickets')
    op.drop_table('support_tickets')
