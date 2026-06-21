"""add_skill_user_id_name_unique

Revision ID: 74877dd07c31
Revises: c7d8e9f0a1b2
Create Date: 2026-06-21 22:07:34.740
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '74877dd07c31'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Clean up duplicates — keep oldest row per (user_id, name)
    op.execute("""
        DELETE FROM skills
        WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY user_id, name ORDER BY created_at ASC, id ASC
                ) AS rn
                FROM skills
            ) t
            WHERE rn > 1
        )
    """)
    # Step 2: Add unique constraint
    op.create_unique_constraint(
        "uq_skill_user_name", "skills", ["user_id", "name"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_skill_user_name", "skills", type_="unique")
