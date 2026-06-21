"""Tests for the diff-based seed loop in ``list_agent_configs``.

When an existing user (>= 1 config) calls ``list_agent_configs``, the route
iterates ``_DEFAULT_AGENT_CONFIGS`` and creates bare defaults for any roles
missing from the user's current config set.  This file verifies that the three
new roles added in Task 1 — ``review_writer``, ``debater``, ``deep_reviewer``
— are created on the next call when the user only has a ``researcher`` config.
"""

from sqlalchemy import func, select

from app.api.routes.agents import list_agent_configs
from app.models import AgentConfig, AgentRole, User


async def _count_configs_for_user(db_session, user_id: str) -> int:
    """Return the number of AgentConfig rows belonging to *user_id*."""
    result = await db_session.execute(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.user_id == user_id)
    )
    return result.scalar_one()


async def test_diff_seed_creates_three_new_defaults_for_existing_user(
    db_session,
    test_user,
):
    """An existing user with 1 config gets the 3 new defaults on next visit.

    Setup:
        * ``test_user`` is already committed by the fixture.
        * We manually create one ``AgentConfig`` with ``role=RESEARCHER``.

    Action:
        Call ``list_agent_configs(user_id, db)`` directly (bypassing FastAPI
        ``Depends`` injection).

    Assertions:
        1. 7 configs total (1 existing + 6 missing defaults created).
        2. The 3 new roles (REVIEW_WRITER, DEBATER, DEEP_REVIEWER) are present.
        3. The 3 new configs have ``is_default=True`` and the expected names.
        4. The original researcher config was not modified.
    """
    # --- Arrange: create the single pre-existing config ---------------------
    existing_config = AgentConfig(
        user_id=test_user.id,
        name="Default Researcher",
        role=AgentRole.RESEARCHER,
        provider="openrouter",
        model="google/gemma-4-31b-it:free",
        strategy="direct",
        system_prompt="You are a research assistant.",
        is_default=True,
    )
    db_session.add(existing_config)
    await db_session.commit()
    await db_session.refresh(existing_config)

    # Sanity check: exactly 1 config before the call
    assert await _count_configs_for_user(db_session, test_user.id) == 1

    # --- Act: call list_agent_configs directly ------------------------------
    configs = await list_agent_configs(str(test_user.id), db_session)

    total = await _count_configs_for_user(db_session, test_user.id)
    assert total == 7, f"Expected 7 configs (1 existing + 6 missing defaults), got {total}"
    assert len(configs) == 7, f"Return list should have 7 items, got {len(configs)}"

    # --- Assert: the 3 new roles are correct --------------------------------
    all_roles = {c.role for c in configs}
    assert AgentRole.REVIEW_WRITER in all_roles, "REVIEW_WRITER missing"
    assert AgentRole.DEBATER in all_roles, "DEBATER missing"
    assert AgentRole.DEEP_REVIEWER in all_roles, "DEEP_REVIEWER missing"

    # --- Assert: new configs have correct names + is_default -----------------
    configs_by_role = {c.role: c for c in configs}

    rw = configs_by_role[AgentRole.REVIEW_WRITER]
    assert rw.name == "Default Review Writer"
    assert rw.is_default is True

    deb = configs_by_role[AgentRole.DEBATER]
    assert deb.name == "Default Debater"
    assert deb.is_default is True

    dr = configs_by_role[AgentRole.DEEP_REVIEWER]
    assert dr.name == "Default Deep Reviewer"
    assert dr.is_default is True

    # --- Assert: existing researcher config was not modified -----------------
    researcher = configs_by_role[AgentRole.RESEARCHER]
    assert researcher.id == existing_config.id
    assert researcher.name == existing_config.name
    assert researcher.is_default == existing_config.is_default
