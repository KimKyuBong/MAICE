"""Add message_id column to LLM logging tables

Revision ID: 20241223_001
Revises: 20241220_001
Create Date: 2024-12-23 20:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20241223_001'
down_revision = '20241220_001'
branch_labels = None
depends_on = None


def upgrade():
    # Add message_id column to llm_prompt_logs table
    op.add_column('llm_prompt_logs', sa.Column('message_id', sa.String(length=255), nullable=True))
    
    # Add message_id column to llm_response_logs table
    op.add_column('llm_response_logs', sa.Column('message_id', sa.String(length=255), nullable=True))
    
    # Create indexes for message_id columns
    op.create_index('ix_llm_prompt_logs_message_id', 'llm_prompt_logs', ['message_id'])
    op.create_index('ix_llm_response_logs_message_id', 'llm_response_logs', ['message_id'])
    
    print("✅ message_id 컬럼 및 인덱스 추가 완료")


def downgrade():
    # Drop indexes
    op.drop_index('ix_llm_response_logs_message_id', table_name='llm_response_logs')
    op.drop_index('ix_llm_prompt_logs_message_id', table_name='llm_prompt_logs')
    
    # Drop columns
    op.drop_column('llm_response_logs', 'message_id')
    op.drop_column('llm_prompt_logs', 'message_id')
    
    print("✅ message_id 컬럼 및 인덱스 제거 완료")
