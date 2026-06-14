"""remove embedding fields from agent_config

Revision ID: c5d8e1f2a3b4
Revises: b4c9d0e1f2a3
Create Date: 2026-06-14 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d8e1f2a3b4'
down_revision: Union[str, None] = 'b4c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('agent_configs', 'embedding_provider')
    op.drop_column('agent_configs', 'embedding_model')


def downgrade() -> None:
    op.add_column('agent_configs', sa.Column('embedding_provider', sa.String(length=50), nullable=True))
    op.add_column('agent_configs', sa.Column('embedding_model', sa.String(length=100), nullable=True))
