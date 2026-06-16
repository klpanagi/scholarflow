"""add workflow executions

Revision ID: f1a2b3c4d5e6
Revises: d6e7f8a9b0c1
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'd6e7f8a9b0c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workflow_executions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.String(length=100), nullable=False),
        sa.Column('workflow_name', sa.String(length=255), nullable=False),
        sa.Column('input_text', sa.Text(), nullable=True),
        sa.Column('paper_id', sa.UUID(), nullable=True),
        sa.Column('agent_assignments', sa.JSON(), nullable=True),
        sa.Column('stages', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['paper_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workflow_executions_user_id', 'workflow_executions', ['user_id'])
    op.create_index('ix_workflow_executions_created_at', 'workflow_executions', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_workflow_executions_created_at')
    op.drop_index('ix_workflow_executions_user_id')
    op.drop_table('workflow_executions')
