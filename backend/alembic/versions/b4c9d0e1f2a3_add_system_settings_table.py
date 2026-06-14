"""add system_settings table

Revision ID: b4c9d0e1f2a3
Revises: a3b8c9d0e1f2
Create Date: 2026-06-14 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b4c9d0e1f2a3'
down_revision: Union[str, None] = 'a3b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('system_settings')
