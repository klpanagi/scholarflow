"""collapse review_writer into writer

Revision ID: g1h2i3j4k5l6
Revises: f2a3b4c5d6e7
Create Date: 2026-06-26 10:00:00.000000

Collapses the separate REVIEW_WRITER role into WRITER.
All agent_configs with role=REVIEW_WRITER are re-tagged as role=WRITER.
"""

from alembic import op


# revision identifiers
revision = "g1h2i3j4k5l6"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE agent_configs SET role = 'WRITER' WHERE role = 'REVIEW_WRITER'")


def downgrade() -> None:
    # Only re-tag configs that were originally Review Writer (by name match)
    op.execute(
        "UPDATE agent_configs SET role = 'REVIEW_WRITER' WHERE role = 'WRITER' AND name = 'Review Writer'"
    )
