"""HTTP tests for the skills endpoints.

Covers ``GET /skills/`` deduplication behaviour. Seed skills are copied per
user with ``is_public=True``, so the (user_id | is_public) query returns N
copies of every seed. ``list_skills()`` must deduplicate by name, preferring
the caller's own skill over a public copy owned by another user.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import Skill, User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _make_user(db_session, email: str, name: str) -> User:
    user = User(
        email=email,
        name=name,
        hashed_password="not-a-real-hash",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _make_skill(
    db_session,
    user_id,
    *,
    name: str,
    description: str = "",
    is_public: bool = False,
    builtin_tools: list[str] | None = None,
) -> Skill:
    skill = Skill(
        user_id=user_id,
        name=name,
        description=description,
        prompt_template=None,
        builtin_tools=builtin_tools or [],
        custom_tools=[],
        input_schema=None,
        output_schema=None,
        tags=[],
        is_public=is_public,
    )
    db_session.add(skill)
    await db_session.commit()
    await db_session.refresh(skill)
    return skill


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


def _token_for(user_id) -> str:
    return create_access_token({"sub": str(user_id), "type": "access"})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------



def _auth_for(user_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token_for(user_id)}"}
class TestListSkillsDedup:
    @pytest.mark.asyncio
    async def test_returns_only_own_skills(self, client, db_session, test_user):
        await _make_skill(db_session, test_user.id, name="my-skill")

        response = await client.get(
            "/api/skills/",
            headers=_auth_for(test_user.id),
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == "my-skill"
        assert body[0]["user_id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_dedupes_public_skills_from_other_users(
        self, client, db_session, test_user
    ):
        other = await _make_user(db_session, "other@example.com", "Other")
        # Caller owns one skill; other user owns two public skills, one with a
        # name that would collide if the caller also had it (they don't, but
        # the dedup path still needs to be exercised).
        await _make_skill(db_session, test_user.id, name="my-private")
        await _make_skill(
            db_session,
            other.id,
            name="shared-public",
            is_public=True,
        )
        await _make_skill(
            db_session,
            other.id,
            name="other-only-public",
            is_public=True,
        )

        response = await client.get(
            "/api/skills/",
            headers=_auth_for(test_user.id),
        )

        assert response.status_code == 200
        body = response.json()
        names = sorted(s["name"] for s in body)
        assert names == ["my-private", "other-only-public", "shared-public"]
        # Caller's own skill must come back as the caller's copy.
        mine = next(s for s in body if s["name"] == "my-private")
        assert mine["user_id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_prefers_own_skill_over_public_with_same_name(
        self, client, db_session, test_user
    ):
        other = await _make_user(db_session, "other@example.com", "Other")
        # Both users have a skill called "eu-horizon". The caller has edited
        # their copy (description differs). The endpoint must return the
        # caller's copy, not the other user's public one.
        await _make_skill(
            db_session,
            test_user.id,
            name="eu-horizon",
            description="caller's edited version",
        )
        await _make_skill(
            db_session,
            other.id,
            name="eu-horizon",
            description="original public seed",
            is_public=True,
        )

        response = await client.get(
            "/api/skills/",
            headers=_auth_for(test_user.id),
        )

        assert response.status_code == 200
        body = response.json()
        # Only one entry for "eu-horizon".
        assert len(body) == 1
        assert body[0]["name"] == "eu-horizon"
        assert body[0]["user_id"] == str(test_user.id)
        assert body[0]["description"] == "caller's edited version"

    @pytest.mark.asyncio
    async def test_excludes_other_users_private_skills(
        self, client, db_session, test_user
    ):
        other = await _make_user(db_session, "other@example.com", "Other")
        await _make_skill(db_session, test_user.id, name="mine")
        # Another user's private skill must NOT leak through.
        await _make_skill(db_session, other.id, name="theirs-private")

        response = await client.get(
            "/api/skills/",
            headers=_auth_for(test_user.id),
        )

        assert response.status_code == 200
        body = response.json()
        names = [s["name"] for s in body]
        assert "theirs-private" not in names
        assert "mine" in names

    @pytest.mark.asyncio
    async def test_unauthorized_without_token(self, client, db_session, test_user):
        await _make_skill(db_session, test_user.id, name="x")

        response = await client.get("/api/skills/")

        assert response.status_code == 401
