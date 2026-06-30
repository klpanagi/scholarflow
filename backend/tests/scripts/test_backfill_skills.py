"""Tests for :mod:`scripts.backfill_skills`.

Covers the required scenarios:
1. partial state (pre-create users with missing skills)
2. idempotency (run twice, assert 0 changes second time)
3. dry-run (row counts unchanged)
4. zero state (fresh user)
5. full state (already-seeded user)

Backfill now creates global (user_id=NULL) rows once, not per-user copies.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import AgentConfig, AgentRole, Skill, Strategy, User
from scripts.backfill_skills import run_backfill


def _test_session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


SEEDED_SKILL_COUNT = 11
SEEDED_CONFIG_COUNT = 14
SEEDED_SKILL_NAMES = frozenset(
    {
        "eu-horizon",
        "academic-writing",
        "project-management",
        "solo-paper-review",
        "paper-review",
        "paper-review-analyze",
        "paper-review-write",
        "literature-review",
        "response-to-author",
        "response-to-editor",
        "issel-paper-review",
    }
)


async def _count_global_skills(db_session) -> int:
    result = await db_session.execute(
        select(func.count()).select_from(Skill).where(Skill.user_id.is_(None))
    )
    return result.scalar_one()


async def _count_global_configs(db_session) -> int:
    result = await db_session.execute(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.user_id.is_(None))
    )
    return result.scalar_one()


async def _count_skills_for_user(db_session, user_id) -> int:
    result = await db_session.execute(
        select(func.count()).select_from(Skill).where(Skill.user_id == user_id)
    )
    return result.scalar_one()


async def _count_configs_for_user(db_session, user_id) -> int:
    result = await db_session.execute(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.user_id == user_id)
    )
    return result.scalar_one()


async def _make_user(db_session, email: str) -> User:
    user = User(
        email=email,
        name=email.split("@")[0].title(),
        hashed_password="not-a-real-hash",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _make_skill(user_id, name: str) -> Skill:
    return Skill(
        user_id=user_id,
        name=name,
        description=f"{name} description",
        builtin_tools=[],
        tags=[],
        is_public=True,
    )


async def test_backfill_creates_global_rows_not_per_user(
    db_session, db_engine
):
    """Backfill creates 11 global skills + 14 global configs once. User rows stay untouched."""
    factory = _test_session_factory(db_engine)
    user_a = await _make_user(db_session, "user-a@example.com")
    user_b = await _make_user(db_session, "user-b@example.com")

    db_session.add(_make_skill(user_a.id, "eu-horizon"))

    for name in (
        "eu-horizon",
        "academic-writing",
        "project-management",
        "solo-paper-review",
    ):
        db_session.add(_make_skill(user_b.id, name))
    db_session.add(
        AgentConfig(
            user_id=user_b.id,
            name="Review Writer",
            role=AgentRole.WRITER,
            provider="opencode",
            model="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            strategy=Strategy.DIRECT,
            tools=[],
            system_prompt="User's pre-existing Review Writer.",
        )
    )
    await db_session.commit()

    assert await _count_skills_for_user(db_session, user_a.id) == 1
    assert await _count_skills_for_user(db_session, user_b.id) == 4
    assert await _count_configs_for_user(db_session, user_a.id) == 0
    assert await _count_configs_for_user(db_session, user_b.id) == 1

    stats = await run_backfill(dry_run=False, session_factory=factory)

    assert await _count_global_skills(db_session) == SEEDED_SKILL_COUNT
    assert await _count_global_configs(db_session) == SEEDED_CONFIG_COUNT

    assert await _count_skills_for_user(db_session, user_a.id) == 1
    assert await _count_skills_for_user(db_session, user_b.id) == 4
    assert await _count_configs_for_user(db_session, user_a.id) == 0
    assert await _count_configs_for_user(db_session, user_b.id) == 1

    assert stats.users_processed == 2
    assert stats.skills_created == SEEDED_SKILL_COUNT
    assert stats.configs_created == SEEDED_CONFIG_COUNT
    assert stats.errors == []


async def test_backfill_is_idempotent(db_session, test_user, db_engine):
    """First run creates 11 global skills + 14 global configs. Second run creates 0."""
    factory = _test_session_factory(db_engine)
    first_stats = await run_backfill(dry_run=False, session_factory=factory)
    assert first_stats.users_processed == 1
    assert first_stats.skills_created == SEEDED_SKILL_COUNT
    assert first_stats.configs_created == SEEDED_CONFIG_COUNT

    second_stats = await run_backfill(dry_run=False, session_factory=factory)
    assert second_stats.users_processed == 1
    assert second_stats.skills_created == 0
    assert second_stats.configs_created == 0
    assert second_stats.errors == []

    assert await _count_global_skills(db_session) == SEEDED_SKILL_COUNT
    assert await _count_global_configs(db_session) == SEEDED_CONFIG_COUNT


async def test_dry_run_makes_no_writes(db_session, test_user, db_engine):
    """Dry-run reports intended changes but does NOT commit them."""
    factory = _test_session_factory(db_engine)
    skills_before = await _count_global_skills(db_session)
    configs_before = await _count_global_configs(db_session)
    assert skills_before == 0
    assert configs_before == 0

    stats = await run_backfill(dry_run=True, session_factory=factory)

    skills_after = await _count_global_skills(db_session)
    configs_after = await _count_global_configs(db_session)

    assert skills_after == skills_before
    assert configs_after == configs_before

    assert stats.users_processed == 1
    assert stats.skills_created == SEEDED_SKILL_COUNT
    assert stats.configs_created == SEEDED_CONFIG_COUNT
    assert stats.errors == []


async def test_backfill_handles_user_with_zero_state(db_session, db_engine):
    """Backfill creates global rows. User's own skill/config count stays 0."""
    factory = _test_session_factory(db_engine)
    user = await _make_user(db_session, "zero-state@example.com")

    assert await _count_skills_for_user(db_session, user.id) == 0
    assert await _count_configs_for_user(db_session, user.id) == 0

    stats = await run_backfill(dry_run=False, session_factory=factory)
    assert stats.users_processed == 1
    assert stats.skills_created == SEEDED_SKILL_COUNT
    assert stats.configs_created == SEEDED_CONFIG_COUNT
    assert stats.errors == []

    assert await _count_global_skills(db_session) == SEEDED_SKILL_COUNT
    assert await _count_global_configs(db_session) == SEEDED_CONFIG_COUNT
    assert await _count_skills_for_user(db_session, user.id) == 0
    assert await _count_configs_for_user(db_session, user.id) == 0


async def test_backfill_handles_user_with_full_state(db_session, test_user, db_engine):
    """User with per-user skills/configs gets no new per-user rows; global seeds exist."""
    factory = _test_session_factory(db_engine)
    for name in SEEDED_SKILL_NAMES:
        db_session.add(_make_skill(test_user.id, name))
    config_map = {
        "Proposal Writer": AgentRole.WRITER,
        "Proposal Reviewer": AgentRole.REVIEWER,
        "Project Manager": AgentRole.MANAGER,
        "Review Writer": AgentRole.WRITER,
    }
    for name, role in config_map.items():
        db_session.add(
            AgentConfig(
                user_id=test_user.id,
                name=name,
                role=role,
                provider="opencode",
                model="gpt-4o",
                temperature=0.7,
                max_tokens=4096,
                strategy=Strategy.DIRECT,
                tools=[],
                system_prompt=f"{name} prompt.",
            )
        )
    await db_session.commit()

    assert await _count_skills_for_user(db_session, test_user.id) == SEEDED_SKILL_COUNT
    assert (
        await _count_configs_for_user(db_session, test_user.id) == 4
    )

    stats = await run_backfill(dry_run=False, session_factory=factory)
    assert stats.users_processed == 1
    assert stats.skills_created == SEEDED_SKILL_COUNT
    assert stats.configs_created == SEEDED_CONFIG_COUNT
    assert stats.errors == []

    assert await _count_global_skills(db_session) == SEEDED_SKILL_COUNT
    assert await _count_global_configs(db_session) == SEEDED_CONFIG_COUNT

    assert await _count_skills_for_user(db_session, test_user.id) == SEEDED_SKILL_COUNT
    assert (
        await _count_configs_for_user(db_session, test_user.id) == 4
    )
