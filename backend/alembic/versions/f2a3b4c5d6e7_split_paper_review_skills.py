"""split paper-review skill into analyze and write variants

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-25 12:00:00.000000

B.2 of the GROBID integration plan — see .matrixx/plans/grobid-integration.md.
Splits the shared ``paper-review`` skill into two siblings for the 4-stage
paper-review workflow:

* ``paper-review-analyze`` (builtin_tools=["extract_citations"]) — linked to
  ``AgentConfig.role`` in {RESEARCHER, REVIEWER} (SearchAgent, ReviewAgent).
* ``paper-review-write`` (builtin_tools=[]) — linked to ``AgentConfig.role``
  in {DEBATER, REVIEW_WRITER} (DebateAgent, ReviewWriterAgent).

The original ``paper-review`` row is left intact. New users pick up the
split skills via ``seed_scholarflow()``; this migration back-fills existing
users. All operations are idempotent (``WHERE NOT EXISTS`` guards on every
INSERT, relying on the ``uq_skill_user_name`` constraint from
``74877dd07c31_add_skill_user_id_name_unique``).
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO skills (
            id, user_id, name, description, prompt_template,
            builtin_tools, custom_tools, input_schema, output_schema,
            tags, is_public, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            src.user_id,
            'paper-review-analyze',
            src.description,
            src.prompt_template,
            ARRAY['extract_citations']::text[],
            src.custom_tools,
            src.input_schema,
            src.output_schema,
            ARRAY['paper-review', 'analyze', 'citations']::text[],
            src.is_public,
            NOW(),
            NOW()
        FROM skills src
        WHERE src.name = 'paper-review'
          AND NOT EXISTS (
              SELECT 1
              FROM skills s
              WHERE s.user_id = src.user_id
                AND s.name = 'paper-review-analyze'
          )
        """
    )

    op.execute(
        """
        INSERT INTO skills (
            id, user_id, name, description, prompt_template,
            builtin_tools, custom_tools, input_schema, output_schema,
            tags, is_public, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            src.user_id,
            'paper-review-write',
            src.description,
            src.prompt_template,
            ARRAY[]::text[],
            src.custom_tools,
            src.input_schema,
            src.output_schema,
            ARRAY['paper-review', 'write']::text[],
            src.is_public,
            NOW(),
            NOW()
        FROM skills src
        WHERE src.name = 'paper-review'
          AND NOT EXISTS (
              SELECT 1
              FROM skills s
              WHERE s.user_id = src.user_id
                AND s.name = 'paper-review-write'
          )
        """
    )

    # M2M: match on role (the dispatch key in app.agents.factory.AGENT_REGISTRY),
    # not on AgentConfig.name which is per-user. PG stores the enum uppercase.
    op.execute(
        """
        INSERT INTO agent_skills (agent_config_id, skill_id)
        SELECT ac.id, s.id
        FROM agent_configs ac
        JOIN skills s ON s.user_id = ac.user_id
        WHERE s.name = 'paper-review-analyze'
          AND ac.role IN ('RESEARCHER', 'REVIEWER')
          AND NOT EXISTS (
              SELECT 1
              FROM agent_skills asm
              WHERE asm.agent_config_id = ac.id
                AND asm.skill_id = s.id
          )
        """
    )

    op.execute(
        """
        INSERT INTO agent_skills (agent_config_id, skill_id)
        SELECT ac.id, s.id
        FROM agent_configs ac
        JOIN skills s ON s.user_id = ac.user_id
        WHERE s.name = 'paper-review-write'
          AND ac.role IN ('DEBATER', 'REVIEW_WRITER')
          AND NOT EXISTS (
              SELECT 1
              FROM agent_skills asm
              WHERE asm.agent_config_id = ac.id
                AND asm.skill_id = s.id
          )
        """
    )


def downgrade() -> None:
    # Best-effort: re-link affected AgentConfigs to the original paper-review
    # (only if the user still has it).
    op.execute(
        """
        INSERT INTO agent_skills (agent_config_id, skill_id)
        SELECT ac.id, s.id
        FROM agent_configs ac
        JOIN skills s ON s.user_id = ac.user_id
        WHERE s.name = 'paper-review'
          AND ac.role IN (
              'RESEARCHER', 'REVIEWER', 'DEBATER', 'REVIEW_WRITER'
          )
          AND NOT EXISTS (
              SELECT 1
              FROM agent_skills asm
              WHERE asm.agent_config_id = ac.id
                AND asm.skill_id = s.id
          )
        """
    )

    # Explicit DELETE (vs CASCADE on the FK) so the operation order stays
    # self-evident and the migration is robust to future schema changes.
    op.execute(
        """
        DELETE FROM agent_skills
        WHERE skill_id IN (
            SELECT id FROM skills
            WHERE name IN ('paper-review-analyze', 'paper-review-write')
        )
        """
    )

    op.execute(
        """
        DELETE FROM skills
        WHERE name IN ('paper-review-analyze', 'paper-review-write')
        """
    )
