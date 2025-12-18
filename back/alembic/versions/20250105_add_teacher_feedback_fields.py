"""add_teacher_feedback_fields

Revision ID: 20250105_teacher_feedback
Revises: 20250104_rubric_v43
Create Date: 2025-01-05

교사 의견 필드 추가:
- item_feedbacks: 각 항목(A1-C2)별 교사 의견 (JSON)
- rubric_overall_feedback: 루브릭 총평
- educational_llm_suggestions: LLM 교육적 활용을 위한 제안사항
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20250105_teacher_feedback'
down_revision = '20250104_rubric_v43'
branch_labels = None
depends_on = None


def upgrade():
    # 컬럼 존재 여부 확인 후 추가 (멱등성)
    from sqlalchemy import inspect
    from alembic import op
    
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('conversation_evaluations')]
    
    # 교사 의견 필드 추가
    if 'item_feedbacks' not in existing_columns:
        op.add_column('conversation_evaluations',
                      sa.Column('item_feedbacks', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                               comment='각 항목별 교사 의견 {"A1": "...", "A2": "...", ...}'))
    
    if 'rubric_overall_feedback' not in existing_columns:
        op.add_column('conversation_evaluations',
                      sa.Column('rubric_overall_feedback', sa.Text(), nullable=True,
                               comment='루브릭 총평'))
    
    if 'educational_llm_suggestions' not in existing_columns:
        op.add_column('conversation_evaluations',
                      sa.Column('educational_llm_suggestions', sa.Text(), nullable=True,
                               comment='LLM 교육적 활용을 위한 제안'))


def downgrade():
    op.drop_column('conversation_evaluations', 'educational_llm_suggestions')
    op.drop_column('conversation_evaluations', 'rubric_overall_feedback')
    op.drop_column('conversation_evaluations', 'item_feedbacks')

