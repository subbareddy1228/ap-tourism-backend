"""temple module - all tables

Revision ID: 001
Revises:
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    # ── temples ────────────────────────────────────────────────────────────
    op.create_table(
        'temples',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('deity', sa.String(100), nullable=False),
        sa.Column('district', sa.String(100), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('dress_code', sa.String(200), nullable=True),
        sa.Column('contact_number', sa.String(20), nullable=True),
        sa.Column('website', sa.String(300), nullable=True),
        sa.Column('images', JSONB(), server_default='[]'),
        sa.Column('timings', JSONB(), server_default='{}'),
        sa.Column('is_featured', sa.Boolean(), default=False),
        sa.Column('total_bookings', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── temple_events ──────────────────────────────────────────────────────
    op.create_table(
        'temple_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('temple_id', UUID(as_uuid=True), sa.ForeignKey('temples.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # ── temple_reviews ─────────────────────────────────────────────────────
    op.create_table(
        'temple_reviews',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('temple_id', UUID(as_uuid=True), sa.ForeignKey('temples.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # ── darshan_types ──────────────────────────────────────────────────────
    op.create_table(
        'darshan_types',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('temple_id', UUID(as_uuid=True), sa.ForeignKey('temples.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('darshan_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), default=0.0),
        sa.Column('duration_minutes', sa.Integer(), default=30),
        sa.Column('max_persons_per_booking', sa.Integer(), default=6),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── darshan_slots ──────────────────────────────────────────────────────
    op.create_table(
        'darshan_slots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('temple_id', UUID(as_uuid=True), sa.ForeignKey('temples.id', ondelete='CASCADE'), nullable=False),
        sa.Column('darshan_type_id', UUID(as_uuid=True), sa.ForeignKey('darshan_types.id', ondelete='CASCADE'), nullable=False),
        sa.Column('slot_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('total_quota', sa.Integer(), nullable=False),
        sa.Column('booked_count', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── darshan_bookings ───────────────────────────────────────────────────
    op.create_table(
        'darshan_bookings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('temple_id', UUID(as_uuid=True), sa.ForeignKey('temples.id', ondelete='CASCADE'), nullable=False),
        sa.Column('slot_id', UUID(as_uuid=True), sa.ForeignKey('darshan_slots.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('booking_reference', sa.String(20), unique=True, nullable=False),
        sa.Column('num_persons', sa.Integer(), nullable=False, default=1),
        sa.Column('total_amount', sa.Float(), default=0.0),
        sa.Column('status', sa.String(20), default='PENDING'),
        sa.Column('payment_id', sa.String(100), nullable=True),
        sa.Column('qr_code', sa.Text(), nullable=True),
        sa.Column('pilgrim_details', JSONB(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── pooja_services ─────────────────────────────────────────────────────
    op.create_table(
        'pooja_services',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('temple_id', UUID(as_uuid=True), sa.ForeignKey('temples.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), default=30),
        sa.Column('max_persons', sa.Integer(), default=10),
        sa.Column('requires_priest', sa.Boolean(), default=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── pooja_slots ────────────────────────────────────────────────────────
    op.create_table(
        'pooja_slots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('service_id', UUID(as_uuid=True), sa.ForeignKey('pooja_services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('slot_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('total_quota', sa.Integer(), nullable=False),
        sa.Column('booked_count', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # ── pooja_bookings ─────────────────────────────────────────────────────
    op.create_table(
        'pooja_bookings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('temple_id', UUID(as_uuid=True), sa.ForeignKey('temples.id', ondelete='CASCADE'), nullable=False),
        sa.Column('service_id', UUID(as_uuid=True), sa.ForeignKey('pooja_services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('slot_id', UUID(as_uuid=True), sa.ForeignKey('pooja_slots.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('booking_reference', sa.String(20), unique=True, nullable=False),
        sa.Column('num_persons', sa.Integer(), nullable=False, default=1),
        sa.Column('total_amount', sa.Float(), default=0.0),
        sa.Column('status', sa.String(20), default='PENDING'),
        sa.Column('payment_id', sa.String(100), nullable=True),
        sa.Column('special_requests', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── prasadam_items ─────────────────────────────────────────────────────
    op.create_table(
        'prasadam_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('temple_id', UUID(as_uuid=True), sa.ForeignKey('temples.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('weight_grams', sa.Integer(), nullable=True),
        sa.Column('is_available', sa.Boolean(), default=True),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # ── prasadam_orders ────────────────────────────────────────────────────
    op.create_table(
        'prasadam_orders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('temple_id', UUID(as_uuid=True), sa.ForeignKey('temples.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('order_reference', sa.String(20), unique=True, nullable=False),
        sa.Column('total_amount', sa.Float(), default=0.0),
        sa.Column('pickup_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), default='PENDING'),
        sa.Column('payment_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── prasadam_order_items ───────────────────────────────────────────────
    op.create_table(
        'prasadam_order_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('prasadam_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', UUID(as_uuid=True), sa.ForeignKey('prasadam_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, default=1),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('subtotal', sa.Float(), nullable=False),
    )


def downgrade():
    op.drop_table('prasadam_order_items')
    op.drop_table('prasadam_orders')
    op.drop_table('prasadam_items')
    op.drop_table('pooja_bookings')
    op.drop_table('pooja_slots')
    op.drop_table('pooja_services')
    op.drop_table('darshan_bookings')
    op.drop_table('darshan_slots')
    op.drop_table('darshan_types')
    op.drop_table('temple_reviews')
    op.drop_table('temple_events')
    op.drop_table('temples')