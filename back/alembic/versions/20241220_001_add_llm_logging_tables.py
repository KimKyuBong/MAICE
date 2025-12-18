"""Add LLM prompt and response logging tables

Revision ID: 20241220_001
Revises: 
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241220_001'
down_revision = 'a799e9e22959'
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables already exist
    from sqlalchemy import inspect
    inspector = inspect(op.get_bind())
    existing_tables = inspector.get_table_names()
    
    # Create llm_prompt_logs table if not exists
    if 'llm_prompt_logs' not in existing_tables:
        op.create_table('llm_prompt_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tool_name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('stream', sa.Boolean(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('timeout', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('input_prompt', sa.Text(), nullable=True),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('messages', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        print("✅ llm_prompt_logs 테이블 생성 완료")
    else:
        print("ℹ️ llm_prompt_logs 테이블이 이미 존재합니다. 건너뜁니다.")
    
    # Create llm_response_logs table if not exists
    if 'llm_response_logs' not in existing_tables:
        op.create_table('llm_response_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tool_name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('response_time_seconds', sa.Float(), nullable=True),
        sa.Column('response_content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        print("✅ llm_response_logs 테이블 생성 완료")
    else:
        print("ℹ️ llm_response_logs 테이블이 이미 존재합니다. 건너뜁니다.")
    
    # Create indexes for better query performance (only if tables were created)
    if 'llm_prompt_logs' not in existing_tables:
        op.create_index('ix_llm_prompt_logs_timestamp', 'llm_prompt_logs', ['timestamp'])
        op.create_index('ix_llm_prompt_logs_tool_name', 'llm_prompt_logs', ['tool_name'])
        op.create_index('ix_llm_prompt_logs_provider', 'llm_prompt_logs', ['provider'])
        op.create_index('ix_llm_prompt_logs_model', 'llm_prompt_logs', ['model'])
    
    if 'llm_response_logs' not in existing_tables:
        op.create_index('ix_llm_response_logs_timestamp', 'llm_response_logs', ['timestamp'])
        op.create_index('ix_llm_response_logs_tool_name', 'llm_response_logs', ['tool_name'])
        op.create_index('ix_llm_response_logs_provider', 'llm_response_logs', ['provider'])
        op.create_index('ix_llm_response_logs_model', 'llm_response_logs', ['model'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_llm_response_logs_model', table_name='llm_response_logs')
    op.drop_index('ix_llm_response_logs_provider', table_name='llm_response_logs')
    op.drop_index('ix_llm_response_logs_tool_name', table_name='llm_response_logs')
    op.drop_index('ix_llm_response_logs_timestamp', table_name='llm_response_logs')
    
    op.drop_index('ix_llm_prompt_logs_model', table_name='llm_prompt_logs')
    op.drop_index('ix_llm_prompt_logs_provider', table_name='llm_prompt_logs')
    op.drop_index('ix_llm_prompt_logs_tool_name', table_name='llm_prompt_logs')
    op.drop_index('ix_llm_prompt_logs_timestamp', table_name='llm_prompt_logs')
    
    # Drop tables
    op.drop_table('llm_response_logs')
    op.drop_table('llm_prompt_logs')
