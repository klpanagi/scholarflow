"""add processing_status to assets

Revision ID: j1k2l3m4n5o6
Revises: h1i2j3k4l5m6
Create Date: 2026-06-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'j1k2l3m4n5o6'
down_revision: Union[str, None] = 'h1i2j3k4l5m6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('assets', sa.Column('processing_status', sa.String(20), nullable=True))
    op.execute("UPDATE assets SET processing_status = 'completed' WHERE processing_status IS NULL")
    op.alter_column('assets', 'processing_status', nullable=False)


def downgrade() -> None:
    op.drop_column('assets', 'processing_status')
