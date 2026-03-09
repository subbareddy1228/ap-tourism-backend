# ============================================================
# alembic/versions/001_create_user_tables.py
# Migration: Create users, addresses, family_members tables
# Author: Garige Sai Manvitha (LEV146)
# Run: alembic upgrade head
# ============================================================

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision  = '001_user_tables'
down_revision = None           # This is the first migration
branch_labels = None
depends_on    = None


def upgrade():
    # -------------------------
    # users table
    # -------------------------
    op.create_table(
        'users',
        sa.Column('id',              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('phone',           sa.String(15),  nullable=False, unique=True),
        sa.Column('email',           sa.String(255), nullable=True,  unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=True),

        sa.Column('full_name',       sa.String(200), nullable=True),
        sa.Column('gender',          sa.String(10),  nullable=True),
        sa.Column('date_of_birth',   sa.DateTime,    nullable=True),
        sa.Column('language',        sa.String(20),  nullable=False, server_default='TELUGU'),

        sa.Column('avatar_url',      sa.String(500), nullable=True),

        sa.Column('role',            sa.String(20),  nullable=False, server_default='TRAVELER'),

        sa.Column('phone_verified',  sa.Boolean,     nullable=False, server_default='false'),
        sa.Column('email_verified',  sa.Boolean,     nullable=False, server_default='false'),
        sa.Column('kyc_status',      sa.String(20),  nullable=False, server_default='PENDING'),

        sa.Column('wallet_balance',  sa.Float,       nullable=False, server_default='0.0'),
        sa.Column('fcm_token',       sa.String(500), nullable=True),

        sa.Column('preferences',     postgresql.JSONB, nullable=True),

        sa.Column('is_active',       sa.Boolean,     nullable=False, server_default='true'),
        sa.Column('deleted_at',      sa.DateTime,    nullable=True),

        sa.Column('created_at',      sa.DateTime,    nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at',      sa.DateTime,    nullable=False, server_default=sa.text('NOW()')),
    )

    # Indexes for fast lookups
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_role',  'users', ['role'])

    # -------------------------
    # addresses table
    # -------------------------
    op.create_table(
        'addresses',
        sa.Column('id',            postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id',       postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column('label',         sa.String(20),  nullable=False, server_default='HOME'),
        sa.Column('address_line1', sa.String(255), nullable=False),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city',          sa.String(100), nullable=False),
        sa.Column('state',         sa.String(100), nullable=False),
        sa.Column('pincode',       sa.String(10),  nullable=False),

        sa.Column('created_at',    sa.DateTime,    nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at',    sa.DateTime,    nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_addresses_user_id', 'addresses', ['user_id'])

    # -------------------------
    # family_members table
    # -------------------------
    op.create_table(
        'family_members',
        sa.Column('id',              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id',         postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column('name',            sa.String(200), nullable=False),
        sa.Column('relation',        sa.String(20),  nullable=False),
        sa.Column('date_of_birth',   sa.DateTime,    nullable=True),
        sa.Column('gender',          sa.String(10),  nullable=True),

        sa.Column('id_proof_type',   sa.String(20),  nullable=True),
        sa.Column('id_proof_number', sa.String(100), nullable=True),

        sa.Column('created_at',      sa.DateTime,    nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at',      sa.DateTime,    nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_family_members_user_id', 'family_members', ['user_id'])


def downgrade():
    op.drop_table('family_members')
    op.drop_table('addresses')
    op.drop_table('users')
