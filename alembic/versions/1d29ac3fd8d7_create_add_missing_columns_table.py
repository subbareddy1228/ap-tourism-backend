"""
b1c2d3e4f5a6_add_missing_columns.py
 
Revision ID  : b1c2d3e4f5a6
Revises      : 4a09aa407a94
Create Date  : 2026-04-06
 
HOW TO USE
──────────
1.  Copy this file into:  alembic/versions/
    Full path:  alembic/versions/b1c2d3e4f5a6_add_missing_columns.py
 
2.  For the coupon table only, run this SQL FIRST (data migration):
        UPDATE coupons SET used_count  = current_uses WHERE current_uses > 0;
        UPDATE coupons SET usage_limit = max_uses     WHERE max_uses IS NOT NULL;
        UPDATE coupons SET coupon_type =
            CASE WHEN is_referral THEN 'referral'
                 WHEN is_public   THEN 'public'
                 ELSE 'private' END;
        UPDATE coupons SET applicable_on = applicable_to
            WHERE applicable_on = 'all' AND applicable_to IS NOT NULL;
 
3.  Then run:  alembic upgrade head
 
4.  To roll back:  alembic downgrade b1c2d3e4f5a6-1
 
Tables changed
──────────────
  bookings          — 19 columns added
  hotel_bookings    —  2 columns added
  vehicle_bookings  —  7 columns added
  guide_bookings    —  1 column  added
  booking_travelers —  1 column  added
  pooja_bookings    —  7 columns fixed (added new, old renamed via data migration)
  prasadam_orders   —  7 columns added
  coupons           —  6 duplicate columns removed
  partner           —  total_reviews type changed String → Integer
  tracking_sessions —  tracker_role enum type corrected
"""
 
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB, UUID
 
revision      = "b1c2d3e4f5a6"
down_revision = "4a09aa407a94"
branch_labels = None
depends_on    = None
 
 
def column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    row = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column}).fetchone()
    return row is not None
 
 
def index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    row = conn.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :i"
    ), {"i": index_name}).fetchone()
    return row is not None
 
 
def add_column_if_missing(table, col):
    if not column_exists(table, col.key):
        op.add_column(table, col)
 
 
def drop_column_if_exists(table, column):
    if column_exists(table, column):
        op.drop_column(table, column)
 
 
def upgrade() -> None:
 
    # ── bookings ──────────────────────────────────────────────────────────────
    add_column_if_missing("bookings", sa.Column("booking_number",      sa.String(20),     nullable=True))
    add_column_if_missing("bookings", sa.Column("booking_date",        sa.Date(),          nullable=True))
    add_column_if_missing("bookings", sa.Column("start_date",          sa.Date(),          nullable=True))
    add_column_if_missing("bookings", sa.Column("end_date",            sa.Date(),          nullable=True))
    add_column_if_missing("bookings", sa.Column("subtotal",            sa.Numeric(10, 2),  server_default="0", nullable=True))
    add_column_if_missing("bookings", sa.Column("discount_amount",     sa.Numeric(10, 2),  server_default="0", nullable=True))
    add_column_if_missing("bookings", sa.Column("tax_amount",          sa.Numeric(10, 2),  server_default="0", nullable=True))
    add_column_if_missing("bookings", sa.Column("convenience_fee",     sa.Numeric(10, 2),  server_default="0", nullable=True))
    add_column_if_missing("bookings", sa.Column("paid_amount",         sa.Numeric(10, 2),  server_default="0", nullable=True))
    add_column_if_missing("bookings", sa.Column("coupon_code",         sa.String(50),      nullable=True))
    add_column_if_missing("bookings", sa.Column("special_requests",    sa.Text(),          nullable=True))
    add_column_if_missing("bookings", sa.Column("contact_details",     JSONB(),            nullable=True))
    add_column_if_missing("bookings", sa.Column("cancellation_reason", sa.Text(),          nullable=True))
    add_column_if_missing("bookings", sa.Column("cancelled_at",        sa.DateTime(),      nullable=True))
    add_column_if_missing("bookings", sa.Column("confirmed_at",        sa.DateTime(),      nullable=True))
    add_column_if_missing("bookings", sa.Column("completed_at",        sa.DateTime(),      nullable=True))
    add_column_if_missing("bookings", sa.Column("refund_amount",       sa.Numeric(10, 2),  nullable=True))
    add_column_if_missing("bookings", sa.Column("refund_status",       sa.String(20),      nullable=True))
    add_column_if_missing("bookings", sa.Column("custom_trip_details", JSONB(),            nullable=True))
 
    if not index_exists("ix_bookings_start_date"):
        op.create_index("ix_bookings_start_date", "bookings", ["start_date"])
    if not index_exists("ix_bookings_booking_number"):
        op.create_index("ix_bookings_booking_number", "bookings", ["booking_number"], unique=True)
 
    # ── hotel_bookings ────────────────────────────────────────────────────────
    add_column_if_missing("hotel_bookings", sa.Column("check_in_time",  sa.String(10), nullable=True))
    add_column_if_missing("hotel_bookings", sa.Column("check_out_time", sa.String(10), nullable=True))
 
    # ── vehicle_bookings ──────────────────────────────────────────────────────
    add_column_if_missing("vehicle_bookings", sa.Column("actual_km",        sa.Numeric(10, 2), nullable=True))
    add_column_if_missing("vehicle_bookings", sa.Column("pickup_lat",       sa.Numeric(10, 7), nullable=True))
    add_column_if_missing("vehicle_bookings", sa.Column("pickup_lng",       sa.Numeric(10, 7), nullable=True))
    add_column_if_missing("vehicle_bookings", sa.Column("drop_lat",         sa.Numeric(10, 7), nullable=True))
    add_column_if_missing("vehicle_bookings", sa.Column("drop_lng",         sa.Numeric(10, 7), nullable=True))
    add_column_if_missing("vehicle_bookings", sa.Column("driver_allowance", sa.Numeric(10, 2), server_default="0", nullable=True))
    add_column_if_missing("vehicle_bookings", sa.Column("toll_charges",     sa.Numeric(10, 2), server_default="0", nullable=True))
 
    # ── guide_bookings ────────────────────────────────────────────────────────
    add_column_if_missing("guide_bookings", sa.Column("destination_id", UUID(as_uuid=True), nullable=True))
 
    # ── booking_travelers ─────────────────────────────────────────────────────
    add_column_if_missing("booking_travelers", sa.Column("family_member_id", UUID(as_uuid=True), nullable=True))
 
    # ── pooja_bookings ────────────────────────────────────────────────────────
    add_column_if_missing("pooja_bookings", sa.Column("pooja_date",           sa.Date(),         nullable=True))
    add_column_if_missing("pooja_bookings", sa.Column("pooja_time",           sa.Time(),         nullable=True))
    add_column_if_missing("pooja_bookings", sa.Column("devotee_names",        JSONB(),           nullable=True))
    add_column_if_missing("pooja_bookings", sa.Column("gothram",              sa.String(100),    nullable=True))
    add_column_if_missing("pooja_bookings", sa.Column("nakshatra",            sa.String(100),    nullable=True))
    add_column_if_missing("pooja_bookings", sa.Column("special_instructions", sa.Text(),         nullable=True))
    add_column_if_missing("pooja_bookings", sa.Column("price",                sa.Numeric(10, 2), nullable=True))
 
    if column_exists("pooja_bookings", "gotram"):
        op.execute("UPDATE pooja_bookings SET gothram = gotram WHERE gotram IS NOT NULL")
        op.drop_column("pooja_bookings", "gotram")
 
    if column_exists("pooja_bookings", "special_requests"):
        op.execute("UPDATE pooja_bookings SET special_instructions = special_requests WHERE special_requests IS NOT NULL")
        op.drop_column("pooja_bookings", "special_requests")
 
    if column_exists("pooja_bookings", "total_amount"):
        op.execute("UPDATE pooja_bookings SET price = total_amount WHERE total_amount IS NOT NULL")
        # only drop total_amount if it's a legacy column not used by the model
        # op.drop_column("pooja_bookings", "total_amount")
 
    # ── prasadam_orders ───────────────────────────────────────────────────────
    add_column_if_missing("prasadam_orders", sa.Column("prasadam_item_id",    UUID(as_uuid=True), nullable=True))
    add_column_if_missing("prasadam_orders", sa.Column("quantity",            sa.Integer(),       server_default="1",       nullable=True))
    add_column_if_missing("prasadam_orders", sa.Column("unit_price",          sa.Numeric(10, 2),  nullable=True))
    add_column_if_missing("prasadam_orders", sa.Column("total_price",         sa.Numeric(10, 2),  nullable=True))
    add_column_if_missing("prasadam_orders", sa.Column("delivery_address_id", UUID(as_uuid=True), nullable=True))
    add_column_if_missing("prasadam_orders", sa.Column("delivery_status",     sa.String(20),      server_default="pending", nullable=True))
    add_column_if_missing("prasadam_orders", sa.Column("tracking_number",     sa.String(100),     nullable=True))
 
    # ── coupons — IMPORTANT: max_uses is kept, only true duplicates dropped ──
    #
    # The original migration dropped max_uses, but the Coupon model uses it.
    # Only drop columns that are genuine renamed duplicates:
    #   applicable_to  → replaced by applicable_on  (already on model)
    #   current_uses   → replaced by used_count      (already on model)
    #   is_public      → replaced by coupon_type     (already on model)
    #   is_referral    → replaced by coupon_type     (already on model)
    #
    # max_uses and max_uses_per_user are KEPT — they are real model columns.
    #
    # Run data migration SQL first (see module docstring).
    drop_column_if_exists("coupons", "applicable_to")
    drop_column_if_exists("coupons", "current_uses")
    drop_column_if_exists("coupons", "is_public")
    drop_column_if_exists("coupons", "is_referral")
    # !! Do NOT drop max_uses or max_uses_per_user !!
 
    # ── partners ──────────────────────────────────────────────────────────────
    op.execute("UPDATE partners SET total_reviews = '0' WHERE total_reviews IS NULL")
    op.alter_column(
        "partners", "total_reviews",
        existing_type=sa.String(10),
        type_=sa.Integer(),
        postgresql_using="total_reviews::integer",
        nullable=False,
        server_default="0",
    )
 
    # ── tracking_sessions ─────────────────────────────────────────────────────
    op.execute("ALTER TABLE tracking_sessions ALTER COLUMN tracker_role TYPE VARCHAR(20)")
    op.execute(
        "UPDATE tracking_sessions SET tracker_role = 'DRIVER' "
        "WHERE tracker_role NOT IN ('DRIVER', 'GUIDE')"
    )
 
 
def downgrade() -> None:
    op.execute("ALTER TABLE tracking_sessions ALTER COLUMN tracker_role TYPE VARCHAR(20)")
 
    op.alter_column(
        "partners", "total_reviews",
        existing_type=sa.Integer(),
        type_=sa.String(10),
        postgresql_using="total_reviews::text",
        nullable=True,
        server_default=None,
    )
 
    # coupons — restore only what was actually dropped
    add_column_if_missing("coupons", sa.Column("applicable_to", sa.String(),  nullable=True))
    add_column_if_missing("coupons", sa.Column("current_uses",  sa.Integer(), server_default="0"))
    add_column_if_missing("coupons", sa.Column("is_public",     sa.Boolean(), server_default="true"))
    add_column_if_missing("coupons", sa.Column("is_referral",   sa.Boolean(), server_default="false"))
 
    for col in ["tracking_number", "delivery_status", "delivery_address_id",
                "total_price", "unit_price", "quantity", "prasadam_item_id"]:
        drop_column_if_exists("prasadam_orders", col)
 
    add_column_if_missing("pooja_bookings", sa.Column("gotram",           sa.String(100), nullable=True))
    add_column_if_missing("pooja_bookings", sa.Column("special_requests", sa.Text(),      nullable=True))
    op.execute("UPDATE pooja_bookings SET gotram = gothram WHERE gothram IS NOT NULL")
    op.execute("UPDATE pooja_bookings SET special_requests = special_instructions WHERE special_instructions IS NOT NULL")
    for col in ["price", "special_instructions", "nakshatra", "gothram", "devotee_names", "pooja_time", "pooja_date"]:
        drop_column_if_exists("pooja_bookings", col)
 
    drop_column_if_exists("booking_travelers", "family_member_id")
    drop_column_if_exists("guide_bookings", "destination_id")
 
    for col in ["toll_charges", "driver_allowance", "drop_lng", "drop_lat", "pickup_lng", "pickup_lat", "actual_km"]:
        drop_column_if_exists("vehicle_bookings", col)
 
    drop_column_if_exists("hotel_bookings", "check_out_time")
    drop_column_if_exists("hotel_bookings", "check_in_time")
 
    if index_exists("ix_bookings_booking_number"):
        op.drop_index("ix_bookings_booking_number", table_name="bookings")
    if index_exists("ix_bookings_start_date"):
        op.drop_index("ix_bookings_start_date", table_name="bookings")
 
    for col in [
        "custom_trip_details", "refund_status", "refund_amount",
        "completed_at", "confirmed_at", "cancelled_at", "cancellation_reason",
        "contact_details", "special_requests", "coupon_code",
        "paid_amount", "convenience_fee", "tax_amount", "discount_amount",
        "subtotal", "end_date", "start_date", "booking_date", "booking_number",
    ]:
        drop_column_if_exists("bookings", col)
 