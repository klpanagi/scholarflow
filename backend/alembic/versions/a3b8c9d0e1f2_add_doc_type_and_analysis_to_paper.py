"""add doc_type and analysis to paper

Revision ID: a3b8c9d0e1f2
Revises: 6527b1e2157b
Create Date: 2026-06-13 21:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a3b8c9d0e1f2'
down_revision: Union[str, None] = '6527b1e2157b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('papers', sa.Column('doc_type', sa.String(50), server_default='other'))
    op.add_column('papers', sa.Column('analysis', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('papers', 'analysis')
    op.drop_column('papers', 'doc_type')
