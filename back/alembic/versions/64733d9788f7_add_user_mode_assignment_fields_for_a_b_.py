"""Add user mode assignment fields for A/B testing

Revision ID: 64733d9788f7
Revises: 20241223_001
Create Date: 2025-09-25 15:51:18.370323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '64733d9788f7'
down_revision: Union[str, None] = '20241223_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name, column_name, conn):
    """Check if a column exists in a table"""
    inspector = inspect(conn)
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)


def table_exists(table_name, conn):
    """Check if a table exists"""
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def index_exists(table_name, index_name, conn):
    """Check if an index exists on a table"""
    inspector = inspect(conn)
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    
    # Drop tables and indexes only if they exist
    if table_exists('llm_response_logs', conn):
        if index_exists('llm_response_logs', 'ix_llm_response_logs_message_id', conn):
            op.drop_index('ix_llm_response_logs_message_id', table_name='llm_response_logs')
        op.drop_table('llm_response_logs')
    
    if table_exists('llm_prompt_logs', conn):
        if index_exists('llm_prompt_logs', 'ix_llm_prompt_logs_message_id', conn):
            op.drop_index('ix_llm_prompt_logs_message_id', table_name='llm_prompt_logs')
        op.drop_table('llm_prompt_logs')
    
    # Add columns only if they don't exist
    if not column_exists('users', 'assigned_mode', conn):
        op.add_column('users', sa.Column('assigned_mode', sa.String(), nullable=True))
    
    if not column_exists('users', 'mode_assigned_at', conn):
        op.add_column('users', sa.Column('mode_assigned_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    
    # Drop columns only if they exist
    if column_exists('users', 'mode_assigned_at', conn):
        op.drop_column('users', 'mode_assigned_at')
    
    if column_exists('users', 'assigned_mode', conn):
        op.drop_column('users', 'assigned_mode')
    
    # Recreate tables only if they don't exist
    if not table_exists('llm_prompt_logs', conn):
        op.create_table('llm_prompt_logs',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('timestamp', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=True),
        sa.Column('tool_name', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column('provider', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
        sa.Column('model', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column('max_tokens', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('stream', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=True),
        sa.Column('temperature', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('timeout', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('max_retries', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('input_prompt', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('messages', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column('input_tokens', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=True),
        sa.Column('message_id', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name='llm_prompt_logs_pkey')
        )
        if not index_exists('llm_prompt_logs', 'ix_llm_prompt_logs_message_id', conn):
            op.create_index('ix_llm_prompt_logs_message_id', 'llm_prompt_logs', ['message_id'], unique=False)
    
    if not table_exists('llm_response_logs', conn):
        op.create_table('llm_response_logs',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('timestamp', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=True),
        sa.Column('tool_name', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column('provider', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
        sa.Column('model', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column('input_tokens', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('output_tokens', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('response_time_seconds', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('response_content', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=True),
        sa.Column('message_id', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name='llm_response_logs_pkey')
        )
        if not index_exists('llm_response_logs', 'ix_llm_response_logs_message_id', conn):
            op.create_index('ix_llm_response_logs_message_id', 'llm_response_logs', ['message_id'], unique=False)
