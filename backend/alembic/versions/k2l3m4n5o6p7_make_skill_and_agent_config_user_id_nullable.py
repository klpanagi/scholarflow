"""make skill and agent config user_id nullable

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-06-30 20:25:00.000000

Changes for global defaults:
- Drop ``uq_skill_user_name`` unique constraint on ``skills(user_id, name)``
- Make ``skills.user_id`` nullable
- Make ``agent_configs.user_id`` nullable
- Add partial unique index ``uq_skill_user_name`` WHERE ``user_id IS NOT NULL``
  on ``skills(user_id, name)``
- Add partial unique index ``uq_skill_global_name`` WHERE ``user_id IS NULL``
  on ``skills(name)``
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, None] = "j1k2l3m4n5o6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop the old unique constraint
    op.drop_constraint("uq_skill_user_name", "skills", type_="unique")

    # 2. Make skills.user_id nullable (for global defaults)
    op.alter_column("skills", "user_id", existing_type=sa.UUID(), nullable=True)

    # 3. Make agent_configs.user_id nullable (for global defaults)
    op.alter_column("agent_configs", "user_id", existing_type=sa.UUID(), nullable=True)

    # 4. Add partial unique index for per-user skills (user_id IS NOT NULL)
    op.create_index(
        "uq_skill_user_name",
        "skills",
        ["user_id", "name"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    # 5. Add partial unique index for global skills (user_id IS NULL)
    op.create_index(
        "uq_skill_global_name",
        "skills",
        ["name"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )


def downgrade() -> None:
    # 1. Drop partial indexes
    op.drop_index("uq_skill_global_name", table_name="skills")
    op.drop_index("uq_skill_user_name", table_name="skills")

    # 2. Revert agent_configs.user_id to NOT NULL
    op.alter_column("agent_configs", "user_id", existing_type=sa.UUID(), nullable=False)

    # 3. Revert skills.user_id to NOT NULL
    op.alter_column("skills", "user_id", existing_type=sa.UUID(), nullable=False)

    # 4. Re-add the old unique constraint (fails if null user_id rows exist)
    op.create_unique_constraint("uq_skill_user_name", "skills", ["user_id", "name"])
