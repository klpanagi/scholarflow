"""add_agent_variant

Revision ID: d0f0a1a130ea
Revises: 74877dd07c31
Create Date: 2026-06-22 16:43:26.207319
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd0f0a1a130ea'
down_revision: Union[str, None] = '74877dd07c31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    """Add variant column to agent_configs table."""
    op.execute("CREATE TYPE agentvariant AS ENUM ('SIMPLE', 'STANDARD', 'DEEP')")
    op.add_column('agent_configs', sa.Column('variant', sa.Enum('SIMPLE', 'STANDARD', 'DEEP', name='agentvariant', create_type=False), nullable=True))


def downgrade() -> None:
    """Remove variant column from agent_configs table."""
    op.drop_column('agent_configs', 'variant')
    op.execute("DROP TYPE agentvariant")
