"""add_teacher_rubric_feedbacks

Revision ID: 20250106_teacher_rubric
Revises: 20250105_teacher_feedback
Create Date: 2025-01-06

교사의 루브릭 평가 의견을 UserModel에 저장
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20250106_teacher_rubric'
down_revision = '20250105_teacher_feedback'
branch_labels = None
depends_on = None


def upgrade():
    # 컬럼 존재 여부 확인 후 추가 (멱등성)
    from sqlalchemy import inspect
    from alembic import op
    
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('users')]
    
    # 교사 루브릭 의견 필드 추가
    if 'rubric_feedbacks' not in existing_columns:
        op.add_column('users',
                      sa.Column('rubric_feedbacks', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                               comment='교사의 루브릭 항목별 의견 {"A1": {"elements": {...}, "overall": "..."}, ...}'))


def downgrade():
    op.drop_column('users', 'rubric_feedbacks')

