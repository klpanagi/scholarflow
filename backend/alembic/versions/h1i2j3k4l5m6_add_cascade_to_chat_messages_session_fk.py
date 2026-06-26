"""add_cascade_to_chat_messages_session_fk

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-06-26 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "h1i2j3k4l5m6"
down_revision: Union[str, None] = "g1h2i3j4k5l6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ON DELETE CASCADE to chat_messages.session_id foreign key.

    Deleting a chat session previously failed with a ForeignKeyViolation
    because chat_messages rows still referenced the session. CASCADE at
    the database level is the durable fix; the SQLAlchemy relationship
    cascade is also configured for in-process deletes.
    """
    op.drop_constraint(
        "chat_messages_session_id_fkey",
        "chat_messages",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "chat_messages_session_id_fkey",
        "chat_messages",
        "chat_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Remove ON DELETE CASCADE from chat_messages.session_id foreign key."""
    op.drop_constraint(
        "chat_messages_session_id_fkey",
        "chat_messages",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "chat_messages_session_id_fkey",
        "chat_messages",
        "chat_sessions",
        ["session_id"],
        ["id"],
    )
