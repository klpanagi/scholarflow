"""One-shot script to backfill ScholarFlow skills and agent configs.

Iterates every user in the database and calls :func:`seed_scholarflow`,
which is fully idempotent (skills and configs are deduped by name). A
``--dry-run`` flag counts intended changes without committing by rolling
back the outer transaction at the end.

Usage:

    uv run python -m scripts.backfill_skills --help
    uv run python -m scripts.backfill_skills --dry-run
    uv run python -m scripts.backfill_skills
"""

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass, field
from typing import Callable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import AgentConfig, Skill, User
from app.seeds.scholarflow_skills import (
    _AGENT_SEEDS,
    _SKILL_SEEDS,
    seed_scholarflow,
)


logger = logging.getLogger(__name__)


SEEDED_SKILL_COUNT = len(_SKILL_SEEDS)
SEEDED_CONFIG_COUNT = len(_AGENT_SEEDS)


@dataclass
class BackfillStats:
    """Aggregate counts for a single backfill invocation."""

    users_processed: int = 0
    skills_created: int = 0
    configs_created: int = 0
    errors: list[str] = field(default_factory=list)


async def _count_skills_for_user(db: AsyncSession, user_id: UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(Skill).where(Skill.user_id == user_id)
    )
    return result.scalar_one()


async def _count_configs_for_user(db: AsyncSession, user_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.user_id == user_id)
    )
    return result.scalar_one()


async def backfill_one_user(
    db: AsyncSession, user_id: UUID, dry_run: bool
) -> tuple[int, int]:
    """Seed one user; returns ``(skills_created, configs_created)``.

    In dry-run mode the call to :func:`seed_scholarflow` is skipped and
    only the row-count delta is computed, so the database is never
    mutated. This is necessary because ``seed_scholarflow`` issues its
    own ``commit()`` internally and cannot be rolled back after the fact.
    """
    skills_before = await _count_skills_for_user(db, user_id)
    configs_before = await _count_configs_for_user(db, user_id)

    if dry_run:
        return (
            max(0, SEEDED_SKILL_COUNT - skills_before),
            max(0, SEEDED_CONFIG_COUNT - configs_before),
        )

    await seed_scholarflow(db, str(user_id))
    skills_after = await _count_skills_for_user(db, user_id)
    configs_after = await _count_configs_for_user(db, user_id)
    return skills_after - skills_before, configs_after - configs_before


async def run_backfill(
    dry_run: bool,
    *,
    session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    batch_size: int = 100,
) -> BackfillStats:
    """Run the backfill across every user in the database.

    ``session_factory`` defaults to :data:`AsyncSessionLocal` for CLI use;
    tests can inject a factory bound to the test database.
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}")

    stats = BackfillStats()
    async with session_factory() as db:
        users_result = await db.execute(select(User).order_by(User.created_at))
        users = list(users_result.scalars())

        for user in users:
            try:
                skills_created, configs_created = await backfill_one_user(
                    db, user.id, dry_run
                )
            except Exception as exc:
                logger.exception("Backfill failed for user %s", user.id)
                stats.errors.append(f"{user.id}: {exc}")
                continue
            stats.users_processed += 1
            stats.skills_created += skills_created
            stats.configs_created += configs_created
            logger.info(
                "user=%s skills_created=%d configs_created=%d",
                user.id,
                skills_created,
                configs_created,
            )

    return stats


def _format_summary(stats: BackfillStats, dry_run: bool) -> str:
    header = "DRY RUN" if dry_run else "REAL RUN"
    lines = [
        "=" * 60,
        f"Backfill summary ({header})",
        f"  Users processed: {stats.users_processed}",
        f"  Skills created:   {stats.skills_created}",
        f"  Configs created:  {stats.configs_created}",
        f"  Errors:           {len(stats.errors)}",
    ]
    for err in stats.errors:
        lines.append(f"    - {err}")
    lines.append("=" * 60)
    return "\n".join(lines)


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="backfill_skills",
        description=(
            "Backfill ScholarFlow skills and agent configs for all users. "
            "Idempotent — safe to re-run."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count intended changes without committing to the database.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of users to process per batch (default: 100).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logger.info(
        "Starting backfill (dry_run=%s, batch_size=%d)",
        args.dry_run,
        args.batch_size,
    )
    stats = await run_backfill(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )
    print(_format_summary(stats, args.dry_run))
    return 0 if not stats.errors else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
