"""add file_key, file_name, parent_message_id to revision_messages

Revision ID: c7d8e9f0a1b2
Revises: b5c6d7e8f9a0
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa

revision = 'c7d8e9f0a1b2'
down_revision = 'b5c6d7e8f9a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('revision_messages', sa.Column('file_key', sa.String(length=500), nullable=True))
    op.add_column('revision_messages', sa.Column('file_name', sa.String(length=255), nullable=True))
    op.add_column('revision_messages', sa.Column('parent_message_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_revision_messages_parent_message_id',
        'revision_messages', 'revision_messages',
        ['parent_message_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_revision_messages_parent_message_id', 'revision_messages', ['parent_message_id'])


def downgrade() -> None:
    op.drop_index('ix_revision_messages_parent_message_id')
    op.drop_constraint('fk_revision_messages_parent_message_id', 'revision_messages', type_='foreignkey')
    op.drop_column('revision_messages', 'parent_message_id')
    op.drop_column('revision_messages', 'file_name')
    op.drop_column('revision_messages', 'file_key')
