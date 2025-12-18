"""add_rubric_v43_checklist

Revision ID: 20250104_rubric_v43
Revises: 20251029_add_conversation_evaluation_subscores
Create Date: 2025-01-04

v4.3 루브릭 체크리스트 방식을 위한 필드 추가:
- checklist_data: 32개 체크리스트 요소 및 evidence 저장 (JSON)
- context_dialogue_coherence_score: C1 대화 일관성 점수 (5점)
- context_learning_support_score: C2 학습 과정 지원성 점수 (5점)
- context_total_score: C영역 총점 (10점)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20250104_rubric_v43'
down_revision = '20251029_add_eval_subscores'
branch_labels = None
depends_on = None


def upgrade():
    # 컬럼 존재 여부 확인 후 추가 (멱등성)
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('conversation_evaluations')]
    
    # PostgreSQL의 경우 JSONB, 그 외에는 JSON
    if 'checklist_data' not in existing_columns:
        op.add_column('conversation_evaluations',
                      sa.Column('checklist_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    if 'context_dialogue_coherence_score' not in existing_columns:
        op.add_column('conversation_evaluations',
                      sa.Column('context_dialogue_coherence_score', sa.Float(), nullable=True))
    
    if 'context_learning_support_score' not in existing_columns:
        op.add_column('conversation_evaluations',
                      sa.Column('context_learning_support_score', sa.Float(), nullable=True))
    
    if 'context_total_score' not in existing_columns:
        op.add_column('conversation_evaluations',
                      sa.Column('context_total_score', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('conversation_evaluations', 'context_total_score')
    op.drop_column('conversation_evaluations', 'context_learning_support_score')
    op.drop_column('conversation_evaluations', 'context_dialogue_coherence_score')
    op.drop_column('conversation_evaluations', 'checklist_data')

