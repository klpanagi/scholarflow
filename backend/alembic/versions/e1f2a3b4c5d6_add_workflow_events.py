"""add workflow_events table

Revision ID: e1f2a3b4c5d6
Revises: d0f0a1a130ea
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = 'e1f2a3b4c5d6'
down_revision = 'd0f0a1a130ea'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workflow_events',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('data', JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(['execution_id'], ['workflow_executions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('execution_id', 'event_id', name='ix_workflow_events_execution_event'),
    )
    op.create_index(op.f('ix_workflow_events_execution_id'), 'workflow_events', ['execution_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_workflow_events_execution_id'), table_name='workflow_events')
    op.drop_table('workflow_events')
