"""collapse review_writer into writer

Revision ID: g1h2i3j4k5l6
Revises: a1b2c3d4e5f6
Create Date: 2026-06-26 10:00:00.000000

Collapses the separate REVIEW_WRITER role into WRITER.

* Re-tags existing ``agent_configs`` rows from ``REVIEW_WRITER`` to
  ``WRITER`` so the Python ``AgentRole`` enum (which no longer has
  ``REVIEW_WRITER``) can load them without raising ``LookupError``.
* Replaces the PostgreSQL ``agentrole`` ENUM type so the obsolete
  ``REVIEW_WRITER`` value is no longer accepted on new inserts — keeps
  the DB schema in sync with the Python ``AgentRole`` definition.

The downgrade reverses both changes. The data downgrade is scoped by
``name = 'Review Writer'`` so it does not affect other ``WRITER``-role
rows that were not part of the original ``REVIEW_WRITER`` cohort.
"""

from alembic import op


# revision identifiers
revision = "g1h2i3j4k5l6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Re-tag existing rows. Must run BEFORE the ENUM type swap below,
    #    because the new ENUM does not include 'REVIEW_WRITER' and the
    #    column cast would fail otherwise.
    op.execute(
        "UPDATE agent_configs SET role = 'WRITER' WHERE role = 'REVIEW_WRITER'"
    )

    # 2. Replace the PostgreSQL agentrole ENUM type to drop the obsolete
    #    REVIEW_WRITER value. Standard pattern: rename old, create new,
    #    cast the column to the new type, drop the old type.
    op.execute("ALTER TYPE agentrole RENAME TO agentrole_old")
    op.execute(
        "CREATE TYPE agentrole AS ENUM ("
        "'RESEARCHER', 'WRITER', 'REVIEWER', 'RECOMMENDER', "
        "'REVISION', 'MANAGER', 'DEBATER', 'DEEP_REVIEWER'"
        ")"
    )
    op.execute(
        "ALTER TABLE agent_configs "
        "ALTER COLUMN role TYPE agentrole "
        "USING role::text::agentrole"
    )
    op.execute("DROP TYPE agentrole_old")


def downgrade() -> None:
    # Re-introduce 'REVIEW_WRITER' in the ENUM type BEFORE re-tagging
    # rows; the UPDATE below would otherwise violate the type's allowed
    # values.
    op.execute("ALTER TYPE agentrole RENAME TO agentrole_old")
    op.execute(
        "CREATE TYPE agentrole AS ENUM ("
        "'RESEARCHER', 'WRITER', 'REVIEWER', 'RECOMMENDER', "
        "'REVISION', 'MANAGER', 'DEBATER', 'DEEP_REVIEWER', "
        "'REVIEW_WRITER'"
        ")"
    )
    op.execute(
        "ALTER TABLE agent_configs "
        "ALTER COLUMN role TYPE agentrole "
        "USING role::text::agentrole"
    )
    op.execute("DROP TYPE agentrole_old")

    # Only re-tag the rows that were originally Review Writer (by name).
    op.execute(
        "UPDATE agent_configs SET role = 'REVIEW_WRITER' "
        "WHERE role = 'WRITER' AND name = 'Review Writer'"
    )
