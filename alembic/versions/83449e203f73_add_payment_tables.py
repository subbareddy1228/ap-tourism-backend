"""add payment tables
Revision ID: 83449e203f73
Revises: 9742f2ae52f7
Create Date: 2026-03-23 15:06:00.839553
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '83449e203f73'
down_revision: Union[str, None] = '9742f2ae52f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums safely — skip if already exists
    op.execute("DO $$ BEGIN CREATE TYPE paymentstatus AS ENUM ('INITIATED','PENDING','SUCCESS','FAILED','REFUNDED','PARTIAL_REFUND'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE paymentmethod AS ENUM ('UPI','CARD','NET_BANKING','WALLET','EMI','PAY_LATER'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    op.create_table(
        'refunds',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('transaction_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('razorpay_refund_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'saved_cards',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('razorpay_token', sa.String(length=200), nullable=True),
        sa.Column('last4', sa.String(length=4), nullable=False),
        sa.Column('card_network', sa.String(length=50), nullable=False),
        sa.Column('card_name', sa.String(length=100), nullable=True),
        sa.Column('expiry_month', sa.Float(), nullable=False),
        sa.Column('expiry_year', sa.Float(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('booking_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('status', sa.Enum('INITIATED', 'PENDING', 'SUCCESS', 'FAILED', 'REFUNDED', 'PARTIAL_REFUND', name='paymentstatus', create_type=False), nullable=False),
        sa.Column('payment_method', sa.Enum('UPI', 'CARD', 'NET_BANKING', 'WALLET', 'EMI', 'PAY_LATER', name='paymentmethod', create_type=False), nullable=True),
        sa.Column('razorpay_order_id', sa.String(length=100), nullable=True),
        sa.Column('razorpay_payment_id', sa.String(length=100), nullable=True),
        sa.Column('razorpay_signature', sa.String(length=255), nullable=True),
        sa.Column('payment_metadata', sa.Text(), nullable=True),
        sa.Column('initiated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('transactions')
    op.drop_table('saved_cards')
    op.drop_table('refunds')