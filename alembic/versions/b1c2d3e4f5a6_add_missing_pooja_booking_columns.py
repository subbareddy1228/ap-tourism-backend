"""add_missing_pooja_booking_columns

Revision ID: b1c2d3e4f5a6
Revises: 96456a858406
Create Date: 2026-04-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b1c2d3e4f5a6'
down_revision = '96456a858406'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make booking_id nullable
    op.alter_column('pooja_bookings', 'booking_id',
        existing_type=sa.UUID(),
        nullable=True)

    # Make user_id nullable
    op.alter_column('pooja_bookings', 'user_id',
        existing_type=sa.UUID(),
        nullable=True)

    op.add_column('pooja_bookings', sa.Column('pooja_date', sa.Date(), nullable=True))
    op.add_column('pooja_bookings', sa.Column('pooja_time', sa.Time(), nullable=True))
    op.add_column('pooja_bookings', sa.Column('devotee_names', postgresql.JSONB(), nullable=True))
    op.add_column('pooja_bookings', sa.Column('gothram', sa.String(100), nullable=True))
    op.add_column('pooja_bookings', sa.Column('nakshatra', sa.String(100), nullable=True))
    op.add_column('pooja_bookings', sa.Column('special_instructions', sa.Text(), nullable=True))
    op.add_column('pooja_bookings', sa.Column('price', sa.Numeric(10, 2), nullable=True))

def downgrade() -> None:
    op.drop_column('pooja_bookings', 'price')
    op.drop_column('pooja_bookings', 'special_instructions')
    op.drop_column('pooja_bookings', 'nakshatra')
    op.drop_column('pooja_bookings', 'gothram')
    op.drop_column('pooja_bookings', 'devotee_names')
    op.drop_column('pooja_bookings', 'pooja_time')
    op.drop_column('pooja_bookings', 'pooja_date')