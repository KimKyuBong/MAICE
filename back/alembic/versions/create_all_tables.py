"""Create all tables with session state fields

Revision ID: create_all_tables
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_all_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('password_hash', sa.String(), nullable=True),
        sa.Column('role', sa.Enum('ADMIN', 'TEACHER', 'STUDENT', name='userrole'), nullable=True),
        sa.Column('access_token', sa.String(), nullable=True),
        sa.Column('question_count', sa.Integer(), nullable=True),
        sa.Column('max_questions', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('individual_evaluations', sa.Integer(), nullable=True),
        sa.Column('group_evaluations', sa.Integer(), nullable=True),
        sa.Column('feedback_submissions', sa.Integer(), nullable=True),
        sa.Column('remaining_questions', sa.Integer(), nullable=True),
        sa.Column('progress_rate', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # ConversationSessions table with state fields
    op.create_table('conversation_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('current_stage', sa.String(), nullable=True),
        sa.Column('stage_metadata', sa.Text(), nullable=True),
        sa.Column('last_message_type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversation_sessions_id'), 'conversation_sessions', ['id'], unique=False)
    
    # Questions table with message type fields
    op.create_table('questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('conversation_session_id', sa.Integer(), nullable=True),
        sa.Column('question_text', sa.String(), nullable=True),
        sa.Column('answer_text', sa.String(), nullable=True),
        sa.Column('image_path', sa.String(), nullable=True),
        sa.Column('message_type', sa.String(), nullable=True),
        sa.Column('request_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('answered_at', sa.DateTime(), nullable=True),
        sa.Column('answered_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['answered_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['conversation_session_id'], ['conversation_sessions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questions_id'), 'questions', ['id'], unique=False)
    
    # SessionSummaries table
    op.create_table('session_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('summary_content', sa.Text(), nullable=False),
        sa.Column('request_id', sa.String(), nullable=True),
        sa.Column('summary_type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['conversation_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Set default values
    op.execute("UPDATE conversation_sessions SET current_stage = 'initial_question' WHERE current_stage IS NULL")
    op.execute("UPDATE questions SET message_type = 'question' WHERE message_type IS NULL")


def downgrade():
    op.drop_table('session_summaries')
    op.drop_table('questions')
    op.drop_table('conversation_sessions')
    op.drop_table('users')

