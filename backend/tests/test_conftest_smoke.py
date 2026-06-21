"""Smoke tests for the DB fixtures added to ``backend/tests/conftest.py``.

These tests exercise ``db_session``, ``test_user``, ``test_config`` and the
autouse ``clean_db`` fixture. They are intentionally small — they only assert
that the wiring works end-to-end against the real test PostgreSQL.
"""

import uuid

from sqlalchemy import func, select

from app.models import AgentConfig, User


async def test_db_session_can_create_and_read_user(db_session):
    """``db_session`` exposes a working ``AsyncSession`` against the test DB."""
    user = User(
        email="db-session-smoke@example.com",
        name="DB Session Smoke",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None

    result = await db_session.execute(select(User).where(User.id == user.id))
    fetched = result.scalar_one()

    assert fetched.email == "db-session-smoke@example.com"
    assert fetched.name == "DB Session Smoke"


async def test_test_user_fixture_creates_user_with_real_uuid(test_user):
    """``test_user`` commits a ``User`` row whose ID is a real UUID."""
    assert isinstance(test_user.id, uuid.UUID)
    assert test_user.id.version == 4
    assert test_user.email == "test-user@example.com"
    assert test_user.is_active is True


async def test_clean_db_truncates_between_tests(db_session):
    """``clean_db`` wipes data tables before each test (autouse, function-scoped)."""
    count_before = await db_session.execute(select(func.count()).select_from(User))
    assert count_before.scalar_one() == 0

    db_session.add(
        User(
            email="clean-db-smoke@example.com",
            name="Clean DB Smoke",
            hashed_password="x",
        )
    )
    await db_session.commit()

    count_after = await db_session.execute(select(func.count()).select_from(User))
    assert count_after.scalar_one() == 1


async def test_test_config_fixture_links_to_test_user(test_config, test_user):
    """``test_config`` creates an ``AgentConfig`` bound to ``test_user``."""
    assert test_config.user_id == test_user.id
    assert test_config.is_default is True
    assert test_config.role.value == "researcher"


async def test_clean_db_cascades_to_agent_configs(db_session, test_config):
    """``clean_db`` uses CASCADE — dependent tables are cleared together.

    The ``test_config`` fixture inserted exactly one ``AgentConfig``; inserting
    a second one still leaves the count at 2, proving TRUNCATE ran in a prior
    test and didn't leave stale FK rows.
    """
    count_before = await db_session.execute(select(func.count()).select_from(AgentConfig))
    assert count_before.scalar_one() == 1

    db_session.add(
        AgentConfig(
            user_id=test_config.user_id,
            name="Second",
            role=test_config.role,
            provider="opencode",
            model="gpt-4o",
        )
    )
    await db_session.commit()

    count_after = await db_session.execute(select(func.count()).select_from(AgentConfig))
    assert count_after.scalar_one() == 2
