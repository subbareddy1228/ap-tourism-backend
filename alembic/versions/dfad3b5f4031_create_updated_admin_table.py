"""add hotel admin review fields
 
Revision ID: a3f1c9e2b841

Revises: b1c2d3e4f5a6

Create Date: 2026-04-06 00:00:00.000000
 
What this migration adds:

  - hotels.rejection_reason  TEXT NULL

  - hotels.admin_note        TEXT NULL

  - hotels.reviewed_at       TIMESTAMP NULL

  - hotels.reviewed_by       UUID NULL  FK -> users.id
 
  Also corrects the is_active server default from TRUE to FALSE so that

  newly submitted PENDING hotels are not publicly visible before admin

  approval. Existing PENDING rows are back-filled to is_active = FALSE.

"""

from alembic import op

import sqlalchemy as sa

from sqlalchemy.dialects import postgresql
 
# ---------------------------------------------------------------------------

# Revision identifiers — used by Alembic.

# down_revision MUST match the `revision` value declared INSIDE the file

# 1d29ac3fd8d7_create_add_missing_columns_table.py  (which is "b1c2d3e4f5a6")

# ---------------------------------------------------------------------------

revision      = "a3f1c9e2b841"

down_revision = '4a09aa407a94'

branch_labels = None

depends_on    = None
 
 
def upgrade() -> None:

    # ── New audit columns on hotels ──────────────────────────────────────────

    op.add_column("hotels", sa.Column("rejection_reason", sa.Text(), nullable=True))

    op.add_column("hotels", sa.Column("admin_note",       sa.Text(), nullable=True))

    op.add_column("hotels", sa.Column("reviewed_at",      sa.DateTime(), nullable=True))

    op.add_column(

        "hotels",

        sa.Column(

            "reviewed_by",

            postgresql.UUID(as_uuid=True),

            sa.ForeignKey("users.id", ondelete="SET NULL"),

            nullable=True,

        ),

    )

    op.create_index("ix_hotels_reviewed_by", "hotels", ["reviewed_by"])
 
    # ── Fix is_active server default: new hotels must be invisible until approved

    op.alter_column(

        "hotels",

        "is_active",

        server_default=sa.text("false"),

        existing_type=sa.Boolean(),

        existing_nullable=False,

    )
 
    # Back-fill: any existing PENDING rows should also be is_active = FALSE

    op.execute("UPDATE hotels SET is_active = FALSE WHERE status = 'PENDING'")
 
 
def downgrade() -> None:

    op.drop_index("ix_hotels_reviewed_by", table_name="hotels")

    op.drop_column("hotels", "reviewed_by")

    op.drop_column("hotels", "reviewed_at")

    op.drop_column("hotels", "admin_note")

    op.drop_column("hotels", "rejection_reason")
 
    op.alter_column(

        "hotels",

        "is_active",

        server_default=sa.text("true"),

        existing_type=sa.Boolean(),

        existing_nullable=False,

    )
 