"""Idempotency tests for :func:`seed_scholarflow`.

Asserts that calling :func:`seed_scholarflow` repeatedly does not create
duplicate ``AgentConfig`` rows. Seeds are now global (user_id=NULL), so
dedup checks query ``user_id IS NULL`` regardless of the ``user_id``
parameter passed to ``seed_scholarflow``.
"""

import pytest
from sqlalchemy import func, select

from app.models import AgentConfig, AgentRole, AgentVariant, Skill, Strategy
from app.seeds.scholarflow_skills import _AGENT_SEEDS, seed_scholarflow


SEEDED_CONFIG_COUNT = len(_AGENT_SEEDS)  # 14
SEEDED_CONFIG_NAMES = frozenset(
    {
        "Proposal Writer",
        "Proposal Reviewer",
        "Project Manager",
        "Review Writer",
        "Simple Debater",
        "Standard Debater",
        "Deep Debater",
        "ISSEL Paper Reviewer",
        "Default Researcher",
        "Default Writer",
        "Default Reviewer",
        "Default Recommender",
        "Default Deep Reviewer",
        "Default Analyzer",
    }
)


async def _count_global_configs(db_session) -> int:
    """Return the number of global AgentConfig rows (user_id IS NULL)."""
    result = await db_session.execute(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.user_id.is_(None))
    )
    return result.scalar_one()


async def _count_global_configs_with_name(db_session, name: str) -> int:
    """Return the number of global AgentConfig rows with the given name."""
    result = await db_session.execute(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.user_id.is_(None), AgentConfig.name == name)
    )
    return result.scalar_one()


async def test_seed_skips_existing_agent_configs_by_name(db_session, test_user):
    """Calling ``seed_scholarflow`` twice creates 14 global configs total, not 28.

    The second call must detect existing global config names and skip them,
    matching the dedup pattern used for skills.
    """
    first = await seed_scholarflow(db_session, test_user.id)
    assert len(first) == SEEDED_CONFIG_COUNT
    assert await _count_global_configs(db_session) == SEEDED_CONFIG_COUNT

    second = await seed_scholarflow(db_session, test_user.id)
    assert second == [], "Second call should create 0 new configs"
    assert await _count_global_configs(db_session) == SEEDED_CONFIG_COUNT, (
        f"Expected {SEEDED_CONFIG_COUNT} global configs after second seed call, "
        "but found duplicates — AgentConfig dedup is broken."
    )


async def test_seed_does_not_create_duplicate_review_writer_config(
    db_session, test_user
):
    """A pre-existing user-level "Review Writer" does not conflict with the global seed.

    Seeds are global (user_id=NULL), so a user's custom "Review Writer"
    (user_id=test_user.id) coexists alongside the global one. The seed
    does not skip "Review Writer" — it creates the global version.
    """
    existing = AgentConfig(
        user_id=test_user.id,
        name="Review Writer",
        role=AgentRole.WRITER,
        provider="opencode",
        model="custom-user-model",
        temperature=0.5,
        max_tokens=2048,
        strategy=Strategy.DIRECT,
        tools=[],
        system_prompt="User-customised Review Writer prompt.",
        is_default=True,
    )
    db_session.add(existing)
    await db_session.commit()
    await db_session.refresh(existing)

    created = await seed_scholarflow(db_session, test_user.id)
    assert len(created) == SEEDED_CONFIG_COUNT

    # Global "Review Writer" was created alongside the user's custom one
    assert await _count_global_configs_with_name(db_session, "Review Writer") == 1

    # User's custom config is still there
    result = await db_session.execute(
        select(AgentConfig).where(
            AgentConfig.user_id == test_user.id,
            AgentConfig.name == "Review Writer",
        )
    )
    survivor = result.scalar_one()
    assert survivor.id == existing.id
    assert survivor.model == "custom-user-model"
    assert survivor.system_prompt == "User-customised Review Writer prompt."


async def test_seed_with_existing_user_creates_only_missing_skills_and_configs(
    db_session, test_user
):
    """Partial user state: seed still creates all 14 global configs.

    User has a pre-existing "Review Writer" (user_id=test_user.id), but
    seeds are global (user_id=NULL) so all 14 configs are created as
    global rows. The user's config coexists with the global ones.
    """
    pre_existing = AgentConfig(
        user_id=test_user.id,
        name="Review Writer",
        role=AgentRole.WRITER,
        provider="opencode",
        model="user-model",
        temperature=0.5,
        max_tokens=2048,
        strategy=Strategy.DIRECT,
        tools=[],
        system_prompt="User's pre-existing Review Writer.",
    )
    db_session.add(pre_existing)
    await db_session.commit()

    skills_before = await db_session.execute(
        select(func.count()).select_from(Skill).where(Skill.user_id == test_user.id)
    )
    assert skills_before.scalar_one() == 0

    created = await seed_scholarflow(db_session, test_user.id)

    # All 14 global configs created (seeds are global, no dedup against user's config)
    assert len(created) == SEEDED_CONFIG_COUNT
    assert await _count_global_configs(db_session) == SEEDED_CONFIG_COUNT

    # User's pre-existing config still exists
    assert await _count_global_configs_with_name(db_session, "Review Writer") == 1
    result = await db_session.execute(
        select(AgentConfig).where(
            AgentConfig.user_id == test_user.id,
            AgentConfig.name == "Review Writer",
        )
    )
    assert result.scalar_one().model == "user-model"


@pytest.mark.unit_db
def test_agent_seeds_contains_three_debater_variants():
    """_AGENT_SEEDS must include 3 debater entries with distinct variants."""
    debater_names = {"Simple Debater", "Standard Debater", "Deep Debater"}
    found = {s["name"] for s in _AGENT_SEEDS if s["role"] == AgentRole.DEBATER}
    assert found == debater_names, (
        f"Expected debater seeds {debater_names}, got {found}"
    )
    variant_map = {s["name"]: s.get("variant") for s in _AGENT_SEEDS if s["role"] == AgentRole.DEBATER}
    assert variant_map == {
        "Simple Debater": AgentVariant.SIMPLE,
        "Standard Debater": AgentVariant.STANDARD,
        "Deep Debater": AgentVariant.DEEP,
    }, f"Variant mismatch: {variant_map}"
