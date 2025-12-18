"""add conversation evaluation subscore columns (3+3, each 0-5)

Revision ID: 20251029_add_eval_subscores
Revises: 20250120_conversation_eval
Create Date: 2025-10-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20251029_add_eval_subscores'
down_revision = '20250120_conversation_eval'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name, conn):
    """Check if a column exists in a table"""
    inspector = inspect(conn)
    try:
        columns = inspector.get_columns(table_name)
        return any(col['name'] == column_name for col in columns)
    except Exception:
        return False


def upgrade() -> None:
    """질문 및 답변 평가 세부 점수 컬럼 추가"""
    conn = op.get_bind()
    
    # 질문 평가 세부 점수 및 합계
    if not column_exists('conversation_evaluations', 'question_professionalism_score', conn):
        op.add_column('conversation_evaluations', sa.Column('question_professionalism_score', sa.Float(), nullable=True))
    
    if not column_exists('conversation_evaluations', 'question_structuring_score', conn):
        op.add_column('conversation_evaluations', sa.Column('question_structuring_score', sa.Float(), nullable=True))
    
    if not column_exists('conversation_evaluations', 'question_context_application_score', conn):
        op.add_column('conversation_evaluations', sa.Column('question_context_application_score', sa.Float(), nullable=True))
    
    if not column_exists('conversation_evaluations', 'question_total_score', conn):
        op.add_column('conversation_evaluations', sa.Column('question_total_score', sa.Float(), nullable=True))

    # 답변 평가 세부 점수 및 합계
    if not column_exists('conversation_evaluations', 'answer_customization_score', conn):
        op.add_column('conversation_evaluations', sa.Column('answer_customization_score', sa.Float(), nullable=True))
    
    if not column_exists('conversation_evaluations', 'answer_systematicity_score', conn):
        op.add_column('conversation_evaluations', sa.Column('answer_systematicity_score', sa.Float(), nullable=True))
    
    if not column_exists('conversation_evaluations', 'answer_expandability_score', conn):
        op.add_column('conversation_evaluations', sa.Column('answer_expandability_score', sa.Float(), nullable=True))
    
    if not column_exists('conversation_evaluations', 'response_total_score', conn):
        op.add_column('conversation_evaluations', sa.Column('response_total_score', sa.Float(), nullable=True))

    # 기존 총점 필드는 그대로 사용(overall_score: 0~30 저장)

    # 더 이상 사용하지 않는 구 필드가 있다면 유지(호환) — 마이그레이션에서 삭제하지 않음


def downgrade() -> None:
    """질문 및 답변 평가 세부 점수 컬럼 제거"""
    conn = op.get_bind()
    
    # 답변 평가 세부 점수 및 합계 제거
    if column_exists('conversation_evaluations', 'response_total_score', conn):
        op.drop_column('conversation_evaluations', 'response_total_score')
    
    if column_exists('conversation_evaluations', 'answer_expandability_score', conn):
        op.drop_column('conversation_evaluations', 'answer_expandability_score')
    
    if column_exists('conversation_evaluations', 'answer_systematicity_score', conn):
        op.drop_column('conversation_evaluations', 'answer_systematicity_score')
    
    if column_exists('conversation_evaluations', 'answer_customization_score', conn):
        op.drop_column('conversation_evaluations', 'answer_customization_score')

    # 질문 평가 세부 점수 및 합계 제거
    if column_exists('conversation_evaluations', 'question_total_score', conn):
        op.drop_column('conversation_evaluations', 'question_total_score')
    
    if column_exists('conversation_evaluations', 'question_context_application_score', conn):
        op.drop_column('conversation_evaluations', 'question_context_application_score')
    
    if column_exists('conversation_evaluations', 'question_structuring_score', conn):
        op.drop_column('conversation_evaluations', 'question_structuring_score')
    
    if column_exists('conversation_evaluations', 'question_professionalism_score', conn):
        op.drop_column('conversation_evaluations', 'question_professionalism_score')


