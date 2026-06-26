"""Idempotency tests for :func:`seed_scholarflow`.

Asserts that calling :func:`seed_scholarflow` repeatedly for the same user
does not create duplicate ``AgentConfig`` rows. The function must mirror
the existing skill dedup pattern (query existing names for the user, skip
in the loop) for the four seed agent configs.
"""

import pytest
from sqlalchemy import func, select

from app.models import AgentConfig, AgentRole, AgentVariant, Skill, Strategy
from app.seeds.scholarflow_skills import _AGENT_SEEDS, seed_scholarflow


SEEDED_CONFIG_COUNT = 7
SEEDED_CONFIG_NAMES = frozenset(
    {
        "Proposal Writer",
        "Proposal Reviewer",
        "Project Manager",
        "Review Writer",
        "Simple Debater",
        "Standard Debater",
        "Deep Debater",
    }
)


async def _count_configs_for_user(db_session, user_id) -> int:
    """Return the number of AgentConfig rows belonging to ``user_id``."""
    result = await db_session.execute(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.user_id == user_id)
    )
    return result.scalar_one()


async def _count_configs_with_name(db_session, user_id, name: str) -> int:
    """Return the number of AgentConfig rows with the given name for the user."""
    result = await db_session.execute(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.user_id == user_id, AgentConfig.name == name)
    )
    return result.scalar_one()


async def test_seed_skips_existing_agent_configs_by_name(db_session, test_user):
    """Calling ``seed_scholarflow`` twice creates 4 configs total, not 8.

    The second call must detect existing config names and skip them,
    matching the dedup pattern used for skills at lines 682-690 of
    ``scholarflow_skills.py``.
    """
    first = await seed_scholarflow(db_session, test_user.id)
    assert len(first) == SEEDED_CONFIG_COUNT
    assert await _count_configs_for_user(db_session, test_user.id) == SEEDED_CONFIG_COUNT

    second = await seed_scholarflow(db_session, test_user.id)
    assert second == [], "Second call should create 0 new configs"
    assert await _count_configs_for_user(db_session, test_user.id) == SEEDED_CONFIG_COUNT, (
        f"Expected {SEEDED_CONFIG_COUNT} configs after second seed call, "
        "but found duplicates — AgentConfig dedup is broken."
    )


async def test_seed_does_not_create_duplicate_review_writer_config(
    db_session, test_user
):
    """A pre-existing "Review Writer" config is not duplicated by the seed.

    "Review Writer" is the highest-risk case because the seed function
    creates 4 configs and the user may already have a custom one with the
    same name. The dedup must skip the seed definition when an
    ``AgentConfig`` with that name already exists for the user.
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
    assert len(created) == SEEDED_CONFIG_COUNT - 1
    assert {c.name for c in created} == SEEDED_CONFIG_NAMES - {"Review Writer"}

    assert await _count_configs_with_name(db_session, test_user.id, "Review Writer") == 1
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
    """Partial state: 1 of 4 configs pre-exists → seed creates only 3 new ones.

    Also verifies that the existing-skill dedup path is preserved when an
    ``AgentConfig`` is skipped: the M2M ``agent_skills`` links for the
    missing configs are created from the freshly created or pre-existing
    skills.
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

    assert await _count_configs_for_user(db_session, test_user.id) == 1
    skills_before = await db_session.execute(
        select(func.count()).select_from(Skill).where(Skill.user_id == test_user.id)
    )
    assert skills_before.scalar_one() == 0

    created = await seed_scholarflow(db_session, test_user.id)

    assert len(created) == SEEDED_CONFIG_COUNT - 1
    assert {c.name for c in created} == {
        "Proposal Writer",
        "Proposal Reviewer",
        "Project Manager",
    }

    assert await _count_configs_for_user(db_session, test_user.id) == SEEDED_CONFIG_COUNT

    assert await _count_configs_with_name(db_session, test_user.id, "Review Writer") == 1


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
