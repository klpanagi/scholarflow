"""add revision sessions and messages

Revision ID: b5c6d7e8f9a0
Revises: a2b3c4d5e6f7
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'b5c6d7e8f9a0'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'revision_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workflow_execution_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('agent_config_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agent_config_id'], ['agent_configs.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['workflow_execution_id'], ['workflow_executions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_revision_sessions_user_id', 'revision_sessions', ['user_id'])
    op.create_index('ix_revision_sessions_workflow_execution_id', 'revision_sessions', ['workflow_execution_id'])
    op.create_index('ix_revision_sessions_created_at', 'revision_sessions', ['created_at'])

    op.create_table(
        'revision_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('revision_session_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['revision_session_id'], ['revision_sessions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_revision_messages_revision_session_id', 'revision_messages', ['revision_session_id'])
    op.create_index('ix_revision_messages_timestamp', 'revision_messages', ['timestamp'])


def downgrade() -> None:
    op.drop_index('ix_revision_messages_timestamp')
    op.drop_index('ix_revision_messages_revision_session_id')
    op.drop_table('revision_messages')
    op.drop_index('ix_revision_sessions_created_at')
    op.drop_index('ix_revision_sessions_workflow_execution_id')
    op.drop_index('ix_revision_sessions_user_id')
    op.drop_table('revision_sessions')
