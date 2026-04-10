"""add_fts_indexes_for_search

Revision ID: 7e220c9e88d7
Revises: c7da0f4c4805
Create Date: 2026-04-10 11:19:50.200868

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '7e220c9e88d7'
down_revision: Union[str, None] = 'c7da0f4c4805'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # temples — has: name, description, deity, district
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_temples_fts
        ON temples USING GIN (
            to_tsvector('english',
                coalesce(name, '') || ' ' ||
                coalesce(description, '') || ' ' ||
                coalesce(deity, '') || ' ' ||
                coalesce(district, '')
            )
        )
    """)

    # hotels — has: name, description, city
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_hotels_fts
        ON hotels USING GIN (
            to_tsvector('english',
                coalesce(name, '') || ' ' ||
                coalesce(description, '') || ' ' ||
                coalesce(city, '')
            )
        )
    """)

    # packages — only name and slug (type is ENUM, causes IMMUTABLE issue)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_packages_fts
        ON packages USING GIN (
            to_tsvector('english',
                coalesce(name, '') || ' ' ||
                coalesce(slug, '')
            )
        )
    """)

    # destinations — has: name, description, tagline, district
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_destinations_fts
        ON destinations USING GIN (
            to_tsvector('english',
                coalesce(name, '') || ' ' ||
                coalesce(description, '') || ' ' ||
                coalesce(tagline, '') || ' ' ||
                coalesce(district, '')
            )
        )
    """)

    # Trigram indexes for fast prefix autocomplete
    op.execute("CREATE INDEX IF NOT EXISTS idx_temples_name_trgm ON temples USING GIN (name gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hotels_name_trgm ON hotels USING GIN (name gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_packages_name_trgm ON packages USING GIN (name gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_destinations_name_trgm ON destinations USING GIN (name gin_trgm_ops);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_temples_fts;")
    op.execute("DROP INDEX IF EXISTS idx_hotels_fts;")
    op.execute("DROP INDEX IF EXISTS idx_packages_fts;")
    op.execute("DROP INDEX IF EXISTS idx_destinations_fts;")
    op.execute("DROP INDEX IF EXISTS idx_temples_name_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_hotels_name_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_packages_name_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_destinations_name_trgm;")