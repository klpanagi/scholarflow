"""HTTP tests for the export and import endpoints.

Covers:
- ``GET /api/export`` — exports the current user's skills and agent
  configurations with skill name associations.
- ``POST /api/import`` — staging endpoint that accepts an ExportBundle,
  detects conflicts, and returns a staging token.
- ``POST /api/import/confirm`` — confirms a staged import.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import AgentConfig, AgentRole, Skill, Strategy, User, agent_skills_table


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


async def _make_agent(
    db_session,
    user_id,
    *,
    name: str,
    role: str = "researcher",
    provider: str = "opencode",
    model: str = "gpt-4o",
    tools: list[str] | None = None,
    skill_ids: list | None = None,
) -> AgentConfig:
    agent = AgentConfig(
        user_id=user_id,
        name=name,
        role=AgentRole(role),
        provider=provider,
        model=model,
        temperature=0.7,
        max_tokens=4096,
        strategy=Strategy.DIRECT,
        tools=tools or [],
        system_prompt="Test system prompt",
        is_default=False,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    if skill_ids:
        for sid in skill_ids:
            stmt = agent_skills_table.insert().values(
                agent_config_id=agent.id, skill_id=sid
            )
            await db_session.execute(stmt)
        await db_session.commit()
        await db_session.refresh(agent)

    return agent


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


def _auth_for(user_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token_for(user_id)}"}


# ---------------------------------------------------------------------------
# Tests — Export
# ---------------------------------------------------------------------------


class TestExportEndpoint:
    @pytest.mark.asyncio
    async def test_export_returns_own_skills_and_agents(self, client, db_session, test_user):
        """Verify all owned skills and agents are returned."""
        skill1 = await _make_skill(
            db_session, test_user.id, name="literature-search",
            description="Search papers",
        )
        skill2 = await _make_skill(
            db_session, test_user.id, name="paper-review",
            description="Review papers",
        )
        agent1 = await _make_agent(
            db_session, test_user.id, name="Scholar",
            role="researcher", tools=["search_papers"],
        )
        agent2 = await _make_agent(
            db_session, test_user.id, name="Writer",
            role="writer",
        )

        response = await client.get(
            "/api/export",
            headers=_auth_for(test_user.id),
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["skills"]) == 2
        assert len(body["agent_configs"]) == 2

        skill_names = sorted(s["name"] for s in body["skills"])
        assert skill_names == ["literature-search", "paper-review"]

        agent_names = sorted(a["name"] for a in body["agent_configs"])
        assert agent_names == ["Scholar", "Writer"]

    @pytest.mark.asyncio
    async def test_export_empty_when_nothing_owned(self, client, db_session, test_user):
        """User with no skills or agents gets empty lists."""
        response = await client.get(
            "/api/export",
            headers=_auth_for(test_user.id),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["skills"] == []
        assert body["agent_configs"] == []

    @pytest.mark.asyncio
    async def test_export_requires_auth(self, client, db_session, test_user):
        """Request without auth token returns 401."""
        response = await client.get("/api/export")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_excludes_other_users_items(self, client, db_session, test_user):
        """Only the current user's data is exported."""
        other = await _make_user(db_session, "other@example.com", "Other")

        await _make_skill(db_session, test_user.id, name="mine")
        await _make_skill(db_session, other.id, name="theirs")

        await _make_agent(db_session, test_user.id, name="My Agent")
        await _make_agent(db_session, other.id, name="Their Agent")

        response = await client.get(
            "/api/export",
            headers=_auth_for(test_user.id),
        )

        assert response.status_code == 200
        body = response.json()

        skill_names = [s["name"] for s in body["skills"]]
        assert skill_names == ["mine"]
        assert "theirs" not in skill_names

        agent_names = [a["name"] for a in body["agent_configs"]]
        assert agent_names == ["My Agent"]
        assert "Their Agent" not in agent_names

    @pytest.mark.asyncio
    async def test_export_response_structure(self, client, db_session, test_user):
        """Verify the response has version, exported_at, skills, agent_configs keys."""
        await _make_skill(db_session, test_user.id, name="s1")

        response = await client.get(
            "/api/export",
            headers=_auth_for(test_user.id),
        )

        assert response.status_code == 200
        body = response.json()

        assert "version" in body
        assert "exported_at" in body
        assert "skills" in body
        assert "agent_configs" in body

        assert body["version"] == 1
        # exported_at should be an ISO datetime string
        assert isinstance(body["exported_at"], str)
        assert "T" in body["exported_at"]

    @pytest.mark.asyncio
    async def test_export_includes_agent_skill_names(self, client, db_session, test_user):
        """Agent export includes skill_names from associated skills."""
        skill_a = await _make_skill(
            db_session, test_user.id, name="skill-alpha",
            builtin_tools=["tool_a"],
        )
        skill_b = await _make_skill(
            db_session, test_user.id, name="skill-beta",
            builtin_tools=["tool_b"],
        )
        agent = await _make_agent(
            db_session, test_user.id, name="MultiSkill Agent",
            skill_ids=[skill_a.id, skill_b.id],
        )

        response = await client.get(
            "/api/export",
            headers=_auth_for(test_user.id),
        )

        assert response.status_code == 200
        body = response.json()

        agent_data = next(a for a in body["agent_configs"] if a["name"] == "MultiSkill Agent")
        assert "skill_names" in agent_data
        assert sorted(agent_data["skill_names"]) == ["skill-alpha", "skill-beta"]


# ---------------------------------------------------------------------------
# Tests — Import
# ---------------------------------------------------------------------------


class TestImportEndpoint:
    def _valid_bundle(self, skill_name: str = "imported-skill") -> dict:
        """Return a minimal but valid ExportBundle payload."""
        return {
            "version": 1,
            "format": "academic-pal-skills-agents-v1",
            "exported_at": "2025-01-15T10:30:00",
            "skills": [
                {
                    "name": skill_name,
                    "description": "An imported skill",
                    "is_public": False,
                    "builtin_tools": [],
                    "custom_tools": [],
                    "tags": [],
                }
            ],
            "agent_configs": [
                {
                    "name": "Imported Agent",
                    "role": "researcher",
                    "provider": "opencode",
                    "model": "gpt-4o",
                    "tools": [],
                    "system_prompt": "Imported system prompt",
                    "skill_names": [skill_name],
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_import_staging_accepts_bundle(self, client, db_session, test_user):
        """POST a valid bundle to /api/import and expect a staging token."""
        bundle = self._valid_bundle()

        response = await client.post(
            "/api/import",
            json=bundle,
            headers=_auth_for(test_user.id),
        )

        assert response.status_code == 200
        body = response.json()
        assert "staging_token" in body
        assert "conflicts" in body

    @pytest.mark.asyncio
    async def test_import_staging_requires_auth(self, client, db_session, test_user):
        """POST without auth token returns 401."""
        bundle = self._valid_bundle()
        response = await client.post("/api/import", json=bundle)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_import_staging_detects_conflicts(
        self, client, db_session, test_user
    ):
        """When a skill with the same name already exists, conflicts list has an entry."""
        await _make_skill(
            db_session, test_user.id, name="existing-skill",
            description="Already here",
        )

        bundle = self._valid_bundle(skill_name="existing-skill")

        response = await client.post(
            "/api/import",
            json=bundle,
            headers=_auth_for(test_user.id),
        )

        assert response.status_code == 200
        body = response.json()
        conflicts = body["conflicts"]
        skill_conflicts = [c for c in conflicts if c.get("type") == "skill"]
        assert len(skill_conflicts) >= 1
        assert skill_conflicts[0]["name"] == "existing-skill"

    @pytest.mark.asyncio
    async def test_import_confirm_requires_auth(self, client, db_session, test_user):
        """POST /api/import/confirm without auth token returns 401."""
        response = await client.post(
            "/api/import/confirm",
            json={"staging_token": "fake-token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_import_confirm_invalid_token(self, client, db_session, test_user):
        """POST /api/import/confirm with a made-up token returns 404."""
        response = await client.post(
            "/api/import/confirm",
            json={"staging_token": "nonexistent-token-abc123"},
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 404
