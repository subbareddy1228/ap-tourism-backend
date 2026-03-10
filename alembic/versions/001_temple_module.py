"""initial - create temple module tables

Revision ID: 001_temple_module
Revises:
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_temple_module"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── temples ──────────────────────────────────────────────────────────────
    op.create_table(
        "temples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("deity", sa.String(100), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("address", sa.Text),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column("is_featured", sa.Boolean, server_default="false"),
        sa.Column("booking_count", sa.Integer, server_default="0"),
        sa.Column("dress_code", sa.Text),
        sa.Column("timings", postgresql.JSON),
        sa.Column("images", postgresql.JSON, server_default="[]"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_temples_deity", "temples", ["deity"])
    op.create_index("ix_temples_district", "temples", ["district"])
    op.create_index("ix_temples_name", "temples", ["name"])

    # ── darshan_types ─────────────────────────────────────────────────────────
    op.create_table(
        "darshan_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("temple_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("temples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Enum("FREE", "SPECIAL_ENTRY", "SUPRABHATA", "VIP",
                                  name="darshantype"), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("price", sa.Numeric(10, 2), server_default="0.00"),
        sa.Column("duration_minutes", sa.Integer),
        sa.Column("what_is_included", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── darshan_slots ─────────────────────────────────────────────────────────
    op.create_table(
        "darshan_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("temple_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("temples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("darshan_type_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("darshan_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot_date", sa.Date, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("total_quota", sa.Integer, nullable=False),
        sa.Column("booked_count", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_darshan_slots_date", "darshan_slots", ["slot_date"])

    # ── darshan_bookings ──────────────────────────────────────────────────────
    op.create_table(
        "darshan_bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("temple_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("temples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("darshan_slots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("devotees_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.Enum("PENDING", "CONFIRMED", "CANCELLED", "EXPIRED",
                                    name="bookingstatus"), server_default="PENDING"),
        sa.Column("total_amount", sa.Numeric(10, 2), server_default="0.00"),
        sa.Column("payment_id", sa.String(255)),
        sa.Column("qr_code", sa.Text),
        sa.Column("booking_reference", sa.String(50), unique=True),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_darshan_bookings_user", "darshan_bookings", ["user_id"])

    # ── pooja_services ────────────────────────────────────────────────────────
    op.create_table(
        "pooja_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("temple_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("temples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("duration_minutes", sa.Integer),
        sa.Column("items_included", sa.Text),
        sa.Column("priest_requirements", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── pooja_slots ───────────────────────────────────────────────────────────
    op.create_table(
        "pooja_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pooja_service_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("pooja_services.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot_date", sa.Date, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("total_quota", sa.Integer, server_default="1"),
        sa.Column("booked_count", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
    )

    # ── pooja_bookings ────────────────────────────────────────────────────────
    op.create_table(
        "pooja_bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pooja_service_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("pooja_services.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("pooja_slots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "CONFIRMED", "CANCELLED", "EXPIRED",
                                    name="bookingstatus", create_type=False),
                  server_default="PENDING"),
        sa.Column("total_amount", sa.Numeric(10, 2)),
        sa.Column("payment_id", sa.String(255)),
        sa.Column("booking_reference", sa.String(50), unique=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_pooja_bookings_user", "pooja_bookings", ["user_id"])

    # ── prasadam_items ────────────────────────────────────────────────────────
    op.create_table(
        "prasadam_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("temple_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("temples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("image_url", sa.String(500)),
        sa.Column("is_available", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── prasadam_orders ───────────────────────────────────────────────────────
    op.create_table(
        "prasadam_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("temple_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("temples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "CONFIRMED", "CANCELLED", "EXPIRED",
                                    name="bookingstatus", create_type=False),
                  server_default="PENDING"),
        sa.Column("total_amount", sa.Numeric(10, 2), server_default="0.00"),
        sa.Column("payment_id", sa.String(255)),
        sa.Column("pickup_date", sa.Date),
        sa.Column("booking_reference", sa.String(50), unique=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_prasadam_orders_user", "prasadam_orders", ["user_id"])

    # ── prasadam_order_items ──────────────────────────────────────────────────
    op.create_table(
        "prasadam_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("prasadam_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prasadam_item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("prasadam_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
    )

    # ── temple_events ─────────────────────────────────────────────────────────
    op.create_table(
        "temple_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("temple_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("temples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("start_time", sa.Time),
        sa.Column("end_time", sa.Time),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── temple_reviews ────────────────────────────────────────────────────────
    op.create_table(
        "temple_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("temple_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("temples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Float, nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("body", sa.Text),
        sa.Column("visit_date", sa.Date),
        sa.Column("is_verified", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_temple_reviews_user", "temple_reviews", ["user_id"])


def downgrade() -> None:
    op.drop_table("temple_reviews")
    op.drop_table("temple_events")
    op.drop_table("prasadam_order_items")
    op.drop_table("prasadam_orders")
    op.drop_table("prasadam_items")
    op.drop_table("pooja_bookings")
    op.drop_table("pooja_slots")
    op.drop_table("pooja_services")
    op.drop_table("darshan_bookings")
    op.drop_table("darshan_slots")
    op.drop_table("darshan_types")
    op.drop_table("temples")
    op.execute("DROP TYPE IF EXISTS darshantype")
    op.execute("DROP TYPE IF EXISTS bookingstatus")