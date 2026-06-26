"""HTTP tests for chat session endpoints.

Covers ``POST /chat/sessions``, ``GET /chat/sessions``, ``GET /chat/sessions/{id}``,
``POST /chat/sessions/{id}/stream``, and ``POST /chat/sessions/{id}/fork``.

Uses the self-contained fixture pattern from ``test_skills.py``: each test
file defines its own ``client`` / ``auth_headers`` so it does not depend on
shared ``db`` / ``client`` / ``auth_headers`` fixtures from ``conftest.py``.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import AgentConfig, AgentRole, Paper, Strategy, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_user(db_session, email: str = "chat-test@example.com", name: str = "Chat Tester") -> User:
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


async def _make_agent_config(
    db_session,
    user_id,
    *,
    name: str = "Test Agent",
    role: AgentRole = AgentRole.RESEARCHER,
    model: str = "gpt-4o",
    provider: str = "opencode",
) -> AgentConfig:
    config = AgentConfig(
        user_id=user_id,
        name=name,
        role=role,
        provider=provider,
        model=model,
        temperature=0.7,
        max_tokens=4096,
        strategy=Strategy.DIRECT,
        tools=[],
        system_prompt="You are a test assistant.",
        is_default=True,
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


async def _make_paper(db_session, owner_id, title: str = "Test Paper") -> Paper:
    paper = Paper(
        owner_id=owner_id,
        title=title,
        authors=["Author One", "Author Two"],
        abstract="Test abstract content for asset tests.",
        doi="10.1000/test",
        year=2024,
        venue="Test Venue",
        minio_key="test/test.pdf",
    )
    db_session.add(paper)
    await db_session.commit()
    await db_session.refresh(paper)
    return paper


async def _make_chat_message(db_session, session_id, role: str = "user", content: str = "Hello"):
    from app.models import ChatMessage
    msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        role=role,
        content=content,
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)
    return msg


def _token_for(user_id) -> str:
    return create_access_token({"sub": str(user_id), "type": "access"})


def _auth_for(user_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token_for(user_id)}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


# ===========================================================================
# Tests: POST /chat/sessions
# ===========================================================================

class TestCreateSession:
    @pytest.mark.asyncio
    async def test_requires_agent_config_id(self, client, db_session, test_user):
        """Omitting ``agent_config_id`` must return 422 (validation error)."""
        response = await client.post(
            "/api/chat/sessions",
            json={"title": "No Agent"},
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_with_valid_agent(self, client, db_session, test_user):
        """A valid ``agent_config_id`` yields 201 with the agent and asset_ids."""
        agent = await _make_agent_config(db_session, test_user.id)

        response = await client.post(
            "/api/chat/sessions",
            json={
                "title": "My Chat",
                "agent_config_id": str(agent.id),
            },
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 200  # FastAPI returns 200 for response_model
        body = response.json()
        assert body["agent_config_id"] == str(agent.id)
        assert body["asset_ids"] == []
        assert body["title"] == "My Chat"

    @pytest.mark.asyncio
    async def test_ownership_check(self, client, db_session, test_user):
        """Using another user's ``agent_config_id`` must return 404."""
        other = await _make_user(db_session, email="other-chat@example.com", name="Other")
        other_agent = await _make_agent_config(db_session, other.id, name="Other Agent")

        response = await client.post(
            "/api/chat/sessions",
            json={"agent_config_id": str(other_agent.id)},
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_asset_cap_21_returns_400(self, client, db_session, test_user):
        """Sending >20 asset IDs must return 400."""
        agent = await _make_agent_config(db_session, test_user.id)
        fake_ids = [str(uuid.uuid4()) for _ in range(21)]

        response = await client.post(
            "/api/chat/sessions",
            json={
                "agent_config_id": str(agent.id),
                "asset_ids": fake_ids,
            },
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 400
        assert "Maximum 20" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_asset_returns_400(self, client, db_session, test_user):
        """A non-existent asset_id must return 400."""
        agent = await _make_agent_config(db_session, test_user.id)

        response = await client.post(
            "/api/chat/sessions",
            json={
                "agent_config_id": str(agent.id),
                "asset_ids": [str(uuid.uuid4())],
            },
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_with_valid_assets(self, client, db_session, test_user):
        """Attaching valid owned assets returns their IDs in the response."""
        agent = await _make_agent_config(db_session, test_user.id)
        paper1 = await _make_paper(db_session, test_user.id, title="Paper A")
        paper2 = await _make_paper(db_session, test_user.id, title="Paper B")

        response = await client.post(
            "/api/chat/sessions",
            json={
                "agent_config_id": str(agent.id),
                "asset_ids": [str(paper1.id), str(paper2.id)],
            },
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["asset_ids"]) == 2
        assert str(paper1.id) in body["asset_ids"]
        assert str(paper2.id) in body["asset_ids"]


# ===========================================================================
# Tests: GET /chat/sessions  and  GET /chat/sessions/{id}
# ===========================================================================

class TestListAndGetSession:
    @pytest.mark.asyncio
    async def test_list_sessions_returns_agent_and_assets(self, client, db_session, test_user):
        """list_sessions returns sessions with agent_config_id and asset_ids."""
        agent = await _make_agent_config(db_session, test_user.id)
        paper = await _make_paper(db_session, test_user.id)

        # Create a session via API so assets are properly linked
        create_resp = await client.post(
            "/api/chat/sessions",
            json={
                "title": "Listable",
                "agent_config_id": str(agent.id),
                "asset_ids": [str(paper.id)],
            },
            headers=_auth_for(test_user.id),
        )
        assert create_resp.status_code == 200

        response = await client.get(
            "/api/chat/sessions",
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) >= 1
        found = [s for s in sessions if s["title"] == "Listable"]
        assert len(found) == 1
        assert found[0]["agent_config_id"] == str(agent.id)
        assert str(paper.id) in found[0]["asset_ids"]

    @pytest.mark.asyncio
    async def test_get_session_returns_agent_and_assets(self, client, db_session, test_user):
        """get_session returns the session with agent and assets."""
        agent = await _make_agent_config(db_session, test_user.id)
        paper = await _make_paper(db_session, test_user.id)

        create_resp = await client.post(
            "/api/chat/sessions",
            json={
                "title": "Fetchable",
                "agent_config_id": str(agent.id),
                "asset_ids": [str(paper.id)],
            },
            headers=_auth_for(test_user.id),
        )
        session_id = create_resp.json()["id"]

        response = await client.get(
            f"/api/chat/sessions/{session_id}",
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["agent_config_id"] == str(agent.id)
        assert str(paper.id) in body["asset_ids"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_session_returns_404(self, client, db_session, test_user):
        """Getting a non-existent session returns 404."""
        response = await client.get(
            f"/api/chat/sessions/{uuid.uuid4()}",
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 404


# ===========================================================================
# Tests: POST /chat/sessions/{id}/stream
# ===========================================================================

class TestStreamChat:
    @pytest.mark.asyncio
    async def test_stream_returns_404_for_nonexistent_session(self, client, db_session, test_user):
        """Streaming from a non-existent session returns 404."""
        response = await client.post(
            f"/api/chat/sessions/{uuid.uuid4()}/stream",
            json={"content": "Hello"},
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stream_chat_dispatches_via_agent(self, client, db_session, test_user):
        """stream_chat with an agent-configured session returns SSE content.

        We mock the LLM call so no real API key is needed. The endpoint
        uses ``_stream_via_agent`` when ``session.agent_config`` is not None.
        """
        agent = await _make_agent_config(db_session, test_user.id)
        paper = await _make_paper(db_session, test_user.id)

        # Create session
        create_resp = await client.post(
            "/api/chat/sessions",
            json={
                "agent_config_id": str(agent.id),
                "asset_ids": [str(paper.id)],
            },
            headers=_auth_for(test_user.id),
        )
        session_id = create_resp.json()["id"]

        # Patch the agent factory and _get_db_session (the latter avoids a
        # separate AsyncSessionLocal connection to the production DB).
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, patch, MagicMock

        mock_result = {"output": "Mocked agent response for testing."}
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def _fake_get_db():
            yield db_session

        with (

            patch("app.agents.factory.create_agent", return_value=mock_agent),
            patch("app.api.routes.chat._get_db_session", _fake_get_db),
        ):
            response = await client.post(
                f"/api/chat/sessions/{session_id}/stream",
                json={"content": "Tell me about this paper"},
                headers=_auth_for(test_user.id),
            )
            assert response.status_code == 200
            text = response.text
            # SSE format: lines starting with "data: {json}"
            assert "data:" in text
            assert "Mocked agent response" in text
            assert '"type": "done"' in text or '"type":"done"' in text

# ===========================================================================
# Tests: POST /chat/sessions/{id}/fork
# ===========================================================================

class TestForkSession:
    @pytest.mark.asyncio
    async def test_fork_propagates_agent_and_assets(self, client, db_session, test_user):
        """fork_session propagates agent_config_id and chat_session_assets."""
        agent = await _make_agent_config(db_session, test_user.id)
        paper = await _make_paper(db_session, test_user.id, title="Forked Paper")

        # Create session with agent + asset
        create_resp = await client.post(
            "/api/chat/sessions",
            json={
                "title": "Original",
                "agent_config_id": str(agent.id),
                "asset_ids": [str(paper.id)],
            },
            headers=_auth_for(test_user.id),
        )
        session_id = create_resp.json()["id"]

        # Create a user message (needed for fork point)
        msg_resp = await client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json={"content": "First message"},
            headers=_auth_for(test_user.id),
        )
        assert msg_resp.status_code == 200
        message_id = msg_resp.json()["id"]

        # Fork from that message
        fork_resp = await client.post(
            f"/api/chat/sessions/{session_id}/fork",
            json={"from_message_id": message_id, "title": "My Fork"},
            headers=_auth_for(test_user.id),
        )
        assert fork_resp.status_code == 200
        forked = fork_resp.json()

        # Agent config propagated
        assert forked["agent_config_id"] == str(agent.id)
        assert forked["title"] == "My Fork"

        # Assets propagated
        assert str(paper.id) in forked["asset_ids"]

    @pytest.mark.asyncio
    async def test_fork_returns_404_for_missing_session(self, client, db_session, test_user):
        """Forking a non-existent session returns 404."""
        fake_msg_id = str(uuid.uuid4())
        response = await client.post(
            f"/api/chat/sessions/{uuid.uuid4()}/fork",
            json={"from_message_id": fake_msg_id},
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_fork_returns_404_for_missing_message(self, client, db_session, test_user):
        """Forking with a non-existent message_id returns 404."""
        agent = await _make_agent_config(db_session, test_user.id)

        create_resp = await client.post(
            "/api/chat/sessions",
            json={"agent_config_id": str(agent.id)},
            headers=_auth_for(test_user.id),
        )
        session_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/chat/sessions/{session_id}/fork",
            json={"from_message_id": str(uuid.uuid4())},
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 404
        assert "Message not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_fork_preserves_model_and_provider(self, client, db_session, test_user):
        """Forked session inherits model and provider from the original."""
        agent = await _make_agent_config(db_session, test_user.id, model="gpt-4o", provider="opencode")

        create_resp = await client.post(
            "/api/chat/sessions",
            json={"agent_config_id": str(agent.id)},
            headers=_auth_for(test_user.id),
        )
        session_id = create_resp.json()["id"]

        msg_resp = await client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json={"content": "seed"},
            headers=_auth_for(test_user.id),
        )
        message_id = msg_resp.json()["id"]

        fork_resp = await client.post(
            f"/api/chat/sessions/{session_id}/fork",
            json={"from_message_id": message_id},
            headers=_auth_for(test_user.id),
        )
        assert fork_resp.status_code == 200
        forked = fork_resp.json()
        assert forked["model"] == "gpt-4o"
        assert forked["provider"] == "opencode"


# ===========================================================================
# Tests: DELETE /chat/sessions/{id} and DELETE /chat/sessions
# ===========================================================================

class TestDeleteSession:
    @pytest.mark.asyncio
    async def test_delete_session_with_messages_cascades(
        self, client, db_session, test_user
    ):
        """Regression: deleting a session that has messages must cascade the
        messages (was failing with ForeignKeyViolation before the cascade fix)."""
        from sqlalchemy import select, text
        from app.models import ChatMessage, ChatSession

        agent = await _make_agent_config(db_session, test_user.id)
        create_resp = await client.post(
            "/api/chat/sessions",
            json={"agent_config_id": str(agent.id), "title": "To Be Deleted"},
            headers=_auth_for(test_user.id),
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        # Seed two messages directly so we don't depend on the streaming pipeline
        await _make_chat_message(db_session, session_id, role="user", content="hi")
        await _make_chat_message(db_session, session_id, role="assistant", content="hello")

        # Sanity: two messages exist for this session
        result = await db_session.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        assert len(result.scalars().all()) == 2

        # Now delete — must succeed (200) thanks to ON DELETE CASCADE
        delete_resp = await client.delete(
            f"/api/chat/sessions/{session_id}",
            headers=_auth_for(test_user.id),
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json() == {"ok": True}

        # Session is gone
        result = await db_session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        assert result.scalar_one_or_none() is None

        # Messages cascaded — assert directly via raw SQL to bypass session cache
        rows = await db_session.execute(
            text("SELECT count(*) FROM chat_messages WHERE session_id = :sid"),
            {"sid": session_id},
        )
        assert rows.scalar() == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_returns_404(self, client, test_user):
        """Deleting a non-existent session returns 404."""
        response = await client.delete(
            f"/api/chat/sessions/{uuid.uuid4()}",
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_other_users_session_returns_404(
        self, client, db_session, test_user
    ):
        """Cannot delete a session belonging to another user."""
        other = await _make_user(db_session, email="other-del@example.com", name="Other")
        other_agent = await _make_agent_config(db_session, other.id, name="Other Agent")
        create_resp = await client.post(
            "/api/chat/sessions",
            json={"agent_config_id": str(other_agent.id), "title": "Other's"},
            headers=_auth_for(other.id),
        )
        session_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/chat/sessions/{session_id}",
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 404


class TestClearAllSessions:
    @pytest.mark.asyncio
    async def test_clear_all_deletes_every_user_session(
        self, client, db_session, test_user
    ):
        """DELETE /chat/sessions removes all sessions (and their messages) for
        the current user and returns the deletion count."""
        from sqlalchemy import select, text
        from app.models import ChatSession

        agent = await _make_agent_config(db_session, test_user.id)
        for i in range(3):
            create_resp = await client.post(
                "/api/chat/sessions",
                json={"agent_config_id": str(agent.id), "title": f"S{i}"},
                headers=_auth_for(test_user.id),
            )
            assert create_resp.status_code == 200
            sid = create_resp.json()["id"]
            await _make_chat_message(db_session, sid, content="x")

        response = await client.delete(
            "/api/chat/sessions",
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 200
        assert response.json() == {"deleted": 3}

        result = await db_session.execute(
            select(ChatSession).where(ChatSession.user_id == test_user.id)
        )
        assert result.scalars().all() == []

        # All messages cascaded too
        rows = await db_session.execute(
            text(
                "SELECT count(*) FROM chat_messages m "
                "JOIN chat_sessions s ON s.id = m.session_id "
                "WHERE s.user_id = :uid"
            ),
            {"uid": test_user.id},
        )
        assert rows.scalar() == 0

    @pytest.mark.asyncio
    async def test_clear_all_with_no_sessions_returns_zero(self, client, test_user):
        """Clearing when the user has no sessions returns ``{"deleted": 0}``."""
        response = await client.delete(
            "/api/chat/sessions",
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 200
        assert response.json() == {"deleted": 0}

    @pytest.mark.asyncio
    async def test_clear_all_does_not_touch_other_users_sessions(
        self, client, db_session, test_user
    ):
        """``DELETE /chat/sessions`` only affects the calling user's sessions."""
        other = await _make_user(db_session, email="keep@example.com", name="Keeper")
        other_agent = await _make_agent_config(db_session, other.id, name="Other Agent")
        create_resp = await client.post(
            "/api/chat/sessions",
            json={"agent_config_id": str(other_agent.id), "title": "Keep me"},
            headers=_auth_for(other.id),
        )
        other_sid = create_resp.json()["id"]

        response = await client.delete(
            "/api/chat/sessions",
            headers=_auth_for(test_user.id),
        )
        assert response.status_code == 200
        assert response.json() == {"deleted": 0}

        # Other user's session still exists
        list_resp = await client.get(
            "/api/chat/sessions",
            headers=_auth_for(other.id),
        )
        assert list_resp.status_code == 200
        ids = [s["id"] for s in list_resp.json()]
        assert other_sid in ids
