"""Add ConversationEvaluation model for session evaluation

Revision ID: 20250120_conversation_eval
Revises: a799e9e22959
Create Date: 2025-01-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250120_conversation_eval'
down_revision: Union[str, None] = '20250108_research_consent'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 테이블이 이미 존재하는지 확인
    from sqlalchemy import inspect
    inspector = inspect(op.get_bind())
    existing_tables = inspector.get_table_names()
    
    if 'conversation_evaluations' not in existing_tables:
        # ConversationEvaluation 테이블 생성
        op.create_table('conversation_evaluations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_session_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('evaluated_by', sa.Integer(), nullable=False),
        sa.Column('question_level_score', sa.Float(), nullable=True),
        sa.Column('question_level_feedback', sa.Text(), nullable=True),
        sa.Column('response_appropriateness_score', sa.Float(), nullable=True),
        sa.Column('response_appropriateness_feedback', sa.Text(), nullable=True),
        sa.Column('educational_context_score', sa.Float(), nullable=True),
        sa.Column('educational_context_feedback', sa.Text(), nullable=True),
        sa.Column('overall_assessment', sa.Text(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('evaluation_status', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_session_id'], ['conversation_sessions.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['evaluated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 인덱스 생성
        op.create_index('idx_conversation_evaluations_session_id', 'conversation_evaluations', ['conversation_session_id'])
        op.create_index('idx_conversation_evaluations_student_id', 'conversation_evaluations', ['student_id'])
        op.create_index('idx_conversation_evaluations_created_at', 'conversation_evaluations', ['created_at'])
        op.create_index('idx_conversation_evaluations_status', 'conversation_evaluations', ['evaluation_status'])
        
        print("✅ conversation_evaluations 테이블 생성 완료")
    else:
        print("ℹ️ conversation_evaluations 테이블이 이미 존재합니다. 건너뜁니다.")


def downgrade() -> None:
    """Downgrade schema."""
    # 인덱스 삭제
    op.drop_index('idx_conversation_evaluations_status', table_name='conversation_evaluations')
    op.drop_index('idx_conversation_evaluations_created_at', table_name='conversation_evaluations')
    op.drop_index('idx_conversation_evaluations_student_id', table_name='conversation_evaluations')
    op.drop_index('idx_conversation_evaluations_session_id', table_name='conversation_evaluations')
    
    # 테이블 삭제
    op.drop_table('conversation_evaluations')

