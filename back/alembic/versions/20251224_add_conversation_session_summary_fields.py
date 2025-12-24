"""Add conversation summary fields to conversation_sessions

Revision ID: 20251224_session_summary_fields
Revises: 20250106_teacher_rubric
Create Date: 2025-12-24

- conversation_summary (TEXT)
- learning_context (TEXT)  # JSON string
- last_summary_at (DATETIME)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251224_session_summary_fields"
down_revision = "20250106_teacher_rubric"
branch_labels = None
depends_on = None


def upgrade():
    # 멱등성: 컬럼 존재 여부 확인 후 추가
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col["name"] for col in inspector.get_columns("conversation_sessions")]

    if "conversation_summary" not in existing_columns:
        op.add_column(
            "conversation_sessions",
            sa.Column("conversation_summary", sa.Text(), nullable=True),
        )

    if "learning_context" not in existing_columns:
        op.add_column(
            "conversation_sessions",
            sa.Column("learning_context", sa.Text(), nullable=True),
        )

    if "last_summary_at" not in existing_columns:
        op.add_column(
            "conversation_sessions",
            sa.Column("last_summary_at", sa.DateTime(), nullable=True),
        )


def downgrade():
    # 역순으로 제거 (존재하지 않아도 IF EXISTS로 안전하게 처리)
    op.execute("ALTER TABLE conversation_sessions DROP COLUMN IF EXISTS last_summary_at")
    op.execute("ALTER TABLE conversation_sessions DROP COLUMN IF EXISTS learning_context")
    op.execute("ALTER TABLE conversation_sessions DROP COLUMN IF EXISTS conversation_summary")


