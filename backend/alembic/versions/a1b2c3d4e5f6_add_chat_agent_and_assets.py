"""add agent and assets to chat sessions

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-06-25 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make existing rows backfill-safe: nullable column
    op.add_column(
        "chat_sessions",
        sa.Column("agent_config_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_sessions_agent_config_id_agent_configs",
        "chat_sessions",
        "agent_configs",
        ["agent_config_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_chat_sessions_agent_config_id",
        "chat_sessions",
        ["agent_config_id"],
    )

    # Join table
    op.create_table(
        "chat_session_assets",
        sa.Column("chat_session_id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column(
            "attached_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chat_session_id"], ["chat_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("chat_session_id", "asset_id"),
    )
    op.create_index(
        "ix_chat_session_assets_chat_session_id",
        "chat_session_assets",
        ["chat_session_id"],
    )
    op.create_index(
        "ix_chat_session_assets_asset_id",
        "chat_session_assets",
        ["asset_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chat_session_assets_asset_id", table_name="chat_session_assets"
    )
    op.drop_index(
        "ix_chat_session_assets_chat_session_id", table_name="chat_session_assets"
    )
    op.drop_table("chat_session_assets")
    op.drop_index(
        "ix_chat_sessions_agent_config_id", table_name="chat_sessions"
    )
    op.drop_constraint(
        "fk_chat_sessions_agent_config_id_agent_configs",
        "chat_sessions",
        type_="foreignkey",
    )
    op.drop_column("chat_sessions", "agent_config_id")
