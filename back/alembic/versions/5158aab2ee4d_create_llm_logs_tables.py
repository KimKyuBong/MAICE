"""create_llm_logs_tables

Revision ID: 5158aab2ee4d
Revises: 3d221d84465c
Create Date: 2025-09-30 14:33:52.943315

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5158aab2ee4d'
down_revision: Union[str, None] = '3d221d84465c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # LLM 프롬프트 로그 테이블 생성
    op.create_table(
        'llm_prompt_logs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('agent_name', sa.String(100), nullable=True),
        sa.Column('prompt_type', sa.String(50), nullable=True),
        sa.Column('prompt_content', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(255), nullable=True),
        sa.Column('model_name', sa.String(100), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Index('idx_llm_prompt_logs_session_id', 'session_id'),
        sa.Index('idx_llm_prompt_logs_user_id', 'user_id'),
        sa.Index('idx_llm_prompt_logs_agent_name', 'agent_name'),
        sa.Index('idx_llm_prompt_logs_created_at', 'created_at')
    )
    
    # LLM 응답 로그 테이블 생성
    op.create_table(
        'llm_response_logs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('prompt_log_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('agent_name', sa.String(100), nullable=True),
        sa.Column('response_content', sa.Text(), nullable=True),
        sa.Column('response_tokens', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Index('idx_llm_response_logs_prompt_log_id', 'prompt_log_id'),
        sa.Index('idx_llm_response_logs_session_id', 'session_id'),
        sa.Index('idx_llm_response_logs_user_id', 'user_id'),
        sa.Index('idx_llm_response_logs_agent_name', 'agent_name'),
        sa.Index('idx_llm_response_logs_created_at', 'created_at'),
        sa.ForeignKeyConstraint(['prompt_log_id'], ['llm_prompt_logs.id'], ondelete='SET NULL')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 테이블 삭제 (역순)
    op.drop_table('llm_response_logs')
    op.drop_table('llm_prompt_logs')
