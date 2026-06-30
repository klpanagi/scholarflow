"""Tests for global-defaults creation and user-override merging in ``list_agent_configs``.

When a user calls ``list_agent_configs``, the route ensures global defaults
(user_id=NULL) exist by calling ``seed_scholarflow`` once. It then merges
global + user configs by name, with the user's version winning on conflicts.
"""

from sqlalchemy import func, select

from app.api.routes.agents import list_agent_configs
from app.models import AgentConfig, AgentRole, User
from app.seeds.scholarflow_skills import _AGENT_SEEDS


async def _count_global_configs(db_session) -> int:
    result = await db_session.execute(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.user_id.is_(None))
    )
    return result.scalar_one()


async def _count_configs_for_user(db_session, user_id) -> int:
    result = await db_session.execute(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.user_id == user_id)
    )
    return result.scalar_one()


async def test_global_defaults_created_on_first_call(db_session, test_user):
    """User with 0 configs calls list_agent_configs; 14 global configs appear."""
    assert await _count_global_configs(db_session) == 0

    configs = await list_agent_configs(str(test_user.id), db_session)

    assert await _count_global_configs(db_session) == len(_AGENT_SEEDS)
    assert len(configs) == len(_AGENT_SEEDS)

    assert await _count_configs_for_user(db_session, test_user.id) == 0


async def test_user_override_config_takes_priority(db_session, test_user):
    """User creates a custom "Proposal Writer"; list_agent_configs returns it instead of global."""
    global_pw = AgentConfig(
        user_id=None,
        name="Proposal Writer",
        role=AgentRole.WRITER,
        provider="openrouter",
        model="deepseek/deepseek-chat-v3-0324:free",
        strategy="direct",
        system_prompt="Global prompt.",
    )
    db_session.add(global_pw)
    await db_session.commit()
    await db_session.refresh(global_pw)

    user_pw = AgentConfig(
        user_id=test_user.id,
        name="Proposal Writer",
        role=AgentRole.WRITER,
        provider="opencode",
        model="my-custom-model",
        strategy="direct",
        system_prompt="User's custom prompt.",
    )
    db_session.add(user_pw)
    await db_session.commit()
    await db_session.refresh(user_pw)

    configs = await list_agent_configs(str(test_user.id), db_session)

    pw = next(c for c in configs if c.name == "Proposal Writer")
    assert pw.id == user_pw.id
    assert pw.model == "my-custom-model"
    assert pw.system_prompt == "User's custom prompt."

    assert len(configs) >= 1
