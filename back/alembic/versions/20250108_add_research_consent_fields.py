"""Add research consent fields to users table

Revision ID: 20250108_add_research_consent_fields
Revises: 64733d9788f7
Create Date: 2025-01-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20250108_research_consent'
down_revision = '5158aab2ee4d'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name, conn):
    """Check if a column exists in a table"""
    inspector = inspect(conn)
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)


def upgrade():
    """연구 참여 동의 관련 필드를 users 테이블에 추가"""
    # Get database connection
    conn = op.get_bind()
    
    # 연구 참여 동의 여부
    if not column_exists('users', 'research_consent', conn):
        op.add_column('users', sa.Column('research_consent', sa.Boolean(), nullable=True, default=False))
    
    # 동의 날짜
    if not column_exists('users', 'research_consent_date', conn):
        op.add_column('users', sa.Column('research_consent_date', sa.DateTime(), nullable=True))
    
    # 동의서 버전 (향후 업데이트 시 새로 동의받기 위한 버전 관리)
    if not column_exists('users', 'research_consent_version', conn):
        op.add_column('users', sa.Column('research_consent_version', sa.String(), nullable=True))
    
    # 동의 철회 날짜
    if not column_exists('users', 'research_consent_withdrawn_at', conn):
        op.add_column('users', sa.Column('research_consent_withdrawn_at', sa.DateTime(), nullable=True))


def downgrade():
    """연구 참여 동의 관련 필드를 users 테이블에서 제거"""
    # Get database connection
    conn = op.get_bind()
    
    # Check if columns exist before dropping them (in reverse order)
    if column_exists('users', 'research_consent_withdrawn_at', conn):
        op.drop_column('users', 'research_consent_withdrawn_at')
    
    if column_exists('users', 'research_consent_version', conn):
        op.drop_column('users', 'research_consent_version')
    
    if column_exists('users', 'research_consent_date', conn):
        op.drop_column('users', 'research_consent_date')
    
    if column_exists('users', 'research_consent', conn):
        op.drop_column('users', 'research_consent')
