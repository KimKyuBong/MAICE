"""Add Google OAuth fields to users table

Revision ID: 20250107_add_google_oauth_fields
Revises: 20250107_000000
Create Date: 2025-01-07 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20250107_add_google_oauth_fields'
down_revision = 'create_all_tables'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name, conn):
    """Check if a column exists in a table"""
    inspector = inspect(conn)
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)


def index_exists(table_name, index_name, conn):
    """Check if an index exists on a table"""
    inspector = inspect(conn)
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade():
    # Get database connection
    conn = op.get_bind()
    
    # Check if columns exist before adding them
    if not column_exists('users', 'google_id', conn):
        op.add_column('users', sa.Column('google_id', sa.String(), nullable=True))
    
    if not column_exists('users', 'google_email', conn):
        op.add_column('users', sa.Column('google_email', sa.String(), nullable=True))
    
    if not column_exists('users', 'google_name', conn):
        op.add_column('users', sa.Column('google_name', sa.String(), nullable=True))
    
    if not column_exists('users', 'google_picture', conn):
        op.add_column('users', sa.Column('google_picture', sa.String(), nullable=True))
    
    if not column_exists('users', 'google_verified_email', conn):
        op.add_column('users', sa.Column('google_verified_email', sa.Boolean(), nullable=True))
    
    # Check if index exists before creating it
    if not index_exists('users', 'ix_users_google_id', conn):
        op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)


def downgrade():
    # Get database connection
    conn = op.get_bind()
    
    # Check if index exists before dropping it
    if index_exists('users', 'ix_users_google_id', conn):
        op.drop_index(op.f('ix_users_google_id'), table_name='users')
    
    # Check if columns exist before dropping them (in reverse order)
    if column_exists('users', 'google_verified_email', conn):
        op.drop_column('users', 'google_verified_email')
    
    if column_exists('users', 'google_picture', conn):
        op.drop_column('users', 'google_picture')
    
    if column_exists('users', 'google_name', conn):
        op.drop_column('users', 'google_name')
    
    if column_exists('users', 'google_email', conn):
        op.drop_column('users', 'google_email')
    
    if column_exists('users', 'google_id', conn):
        op.drop_column('users', 'google_id')
