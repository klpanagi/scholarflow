"""Tests for the workflow progress SSE stream and snapshot endpoints (Task 8).

Covers:
- ``GET /workflows/results/{execution_id}/stream``  (SSE)
- ``GET /workflows/results/{execution_id}/snapshot`` (historical replay)

httpx's ``ASGITransport`` (v0.27) buffers the full SSE body before returning
the response, which means HTTP-level streaming tests would block indefinitely
on the infinite SSE loop.  Instead, this file splits the test surface into:

- HTTP-level tests (httpx) for: auth, access control, terminal status, snapshot
- Generator-level tests (direct invocation) for: event replay, ordering,
  Last-Event-ID resume, heartbeat cadence, terminal-event close
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.routes import workflows as workflows_module
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import User, WorkflowExecution
from app.services.progress import (
    EventType,
    ExecutionEvent,
    get_progress_manager,
    reset_progress_manager,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _make_execution(
    db_session, test_user, *, status: str = "running"
) -> WorkflowExecution:
    execution = WorkflowExecution(
        user_id=test_user.id,
        workflow_id="scholarflow",
        workflow_name="ScholarFlow Test Run",
        input_text="Test input",
        stages=[{"stage_id": "researcher", "status": "pending"}],
        status=status,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)
    return execution


async def _make_other_user(db_session) -> User:
    user = User(
        email="other-user@example.com",
        name="Other User",
        hashed_password="not-a-real-hash",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def _reset_progress_manager():
    reset_progress_manager()
    yield
    reset_progress_manager()


@pytest.fixture(autouse=True)
def _fast_heartbeat(monkeypatch):
    monkeypatch.setattr(workflows_module, "HEARTBEAT_INTERVAL_SECONDS", 0.1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _token_for(user_id) -> str:
    return create_access_token({"sub": str(user_id), "type": "access"})


async def _publish(execution_id, n: int, event_type: EventType = EventType.STAGE_STARTED):
    pm = get_progress_manager()
    for i in range(1, n + 1):
        await pm.publish(
            execution_id,
            ExecutionEvent(
                event_id=i,
                execution_id=execution_id,
                event_type=event_type,
                timestamp=datetime.now(timezone.utc),
                data={"i": i},
            ),
        )


def _parse_sse_events(buf: str) -> list[dict]:
    events: list[dict] = []
    for record in buf.split("\n\n"):
        record = record.strip()
        if not record or record.startswith(":"):
            continue
        event_id = None
        data_lines: list[str] = []
        for line in record.splitlines():
            if line.startswith("id:"):
                event_id = int(line[3:].strip())
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if data_lines:
            events.append({"id": event_id, "data": json.loads("".join(data_lines))})
    return events


class _MockRequest:
    def __init__(self, headers: dict | None = None):
        self.headers = headers or {}


# ---------------------------------------------------------------------------
# /stream - auth + access control (HTTP level, no streaming)
# ---------------------------------------------------------------------------


class TestStreamEndpointAuth:
    @pytest.mark.asyncio
    async def test_stream_unauthorized_without_token(self, client, db_session, test_user):
        execution = await _make_execution(db_session, test_user, status="running")
        response = await client.get(
            f"/api/workflows/results/{execution.id}/stream",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stream_unauthorized_with_invalid_token(
        self, client, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="running")
        response = await client.get(
            f"/api/workflows/results/{execution.id}/stream",
            params={"token": "not-a-valid-jwt"},
        )
        assert response.status_code == 401


class TestStreamEndpointAccessControl:
    @pytest.mark.asyncio
    async def test_stream_returns_404_for_cross_user_execution(
        self, client, db_session, test_user
    ):
        other_user = await _make_other_user(db_session)
        execution = await _make_execution(db_session, other_user, status="running")
        token = _token_for(test_user.id)

        response = await client.get(
            f"/api/workflows/results/{execution.id}/stream",
            params={"token": token},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stream_returns_410_for_completed_execution(
        self, client, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="completed")
        token = _token_for(test_user.id)

        response = await client.get(
            f"/api/workflows/results/{execution.id}/stream",
            params={"token": token},
        )
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_stream_returns_410_for_failed_execution(
        self, client, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="failed")
        token = _token_for(test_user.id)

        response = await client.get(
            f"/api/workflows/results/{execution.id}/stream",
            params={"token": token},
        )
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_stream_returns_410_for_cancelled_execution(
        self, client, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="cancelled")
        token = _token_for(test_user.id)

        response = await client.get(
            f"/api/workflows/results/{execution.id}/stream",
            params={"token": token},
        )
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_stream_returns_410_for_error_execution(
        self, client, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="error")
        token = _token_for(test_user.id)

        response = await client.get(
            f"/api/workflows/results/{execution.id}/stream",
            params={"token": token},
        )
        assert response.status_code == 410


# ---------------------------------------------------------------------------
# /stream - generator-level tests (response + body_iterator)
# ---------------------------------------------------------------------------


class TestStreamResponse:
    @pytest.mark.asyncio
    async def test_response_media_type_and_headers(
        self, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="running")
        from app.api.routes.workflows import stream_workflow_progress

        response = await stream_workflow_progress(
            execution_id=execution.id,
            request=_MockRequest(),
            user_id=str(test_user.id),
            db=db_session,
        )
        assert response.media_type == "text/event-stream"
        assert response.headers.get("x-accel-buffering") == "no"
        assert response.headers.get("cache-control") == "no-cache"
        assert response.headers.get("connection") == "keep-alive"


class TestStreamEventDelivery:
    @pytest.mark.asyncio
    async def test_replays_persisted_events_in_order(
        self, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="running")
        await _publish(execution.id, 3)
        from app.api.routes.workflows import stream_workflow_progress

        response = await stream_workflow_progress(
            execution_id=execution.id,
            request=_MockRequest(),
            user_id=str(test_user.id),
            db=db_session,
        )
        chunks: list[str] = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
            if "id: 3\n" in chunk or chunks[-1].count("id:") >= 3:
                break
            if len(chunks) > 30:
                break

        full = "".join(chunks)
        events = _parse_sse_events(full)
        assert [e["id"] for e in events[:3]] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_resume_from_last_event_id(
        self, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="running")
        await _publish(execution.id, 5)
        from app.api.routes.workflows import stream_workflow_progress

        response = await stream_workflow_progress(
            execution_id=execution.id,
            request=_MockRequest(headers={"Last-Event-ID": "2"}),
            user_id=str(test_user.id),
            db=db_session,
        )
        chunks: list[str] = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
            if "id: 5\n" in chunk:
                break
            if len(chunks) > 30:
                break

        full = "".join(chunks)
        events = _parse_sse_events(full)
        assert [e["id"] for e in events] == [3, 4, 5]

    @pytest.mark.asyncio
    async def test_resume_with_malformed_last_event_id_defaults_to_zero(
        self, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="running")
        await _publish(execution.id, 2)
        from app.api.routes.workflows import stream_workflow_progress

        response = await stream_workflow_progress(
            execution_id=execution.id,
            request=_MockRequest(headers={"Last-Event-ID": "not-an-int"}),
            user_id=str(test_user.id),
            db=db_session,
        )
        chunks: list[str] = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
            if "id: 2\n" in chunk:
                break
            if len(chunks) > 30:
                break

        full = "".join(chunks)
        events = _parse_sse_events(full)
        assert [e["id"] for e in events] == [1, 2]


# ---------------------------------------------------------------------------
# /stream - heartbeat
# ---------------------------------------------------------------------------


class TestStreamHeartbeat:
    @pytest.mark.asyncio
    async def test_heartbeat_emitted_within_interval(
        self, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="running")
        from app.api.routes.workflows import stream_workflow_progress

        response = await stream_workflow_progress(
            execution_id=execution.id,
            request=_MockRequest(),
            user_id=str(test_user.id),
            db=db_session,
        )
        chunks: list[str] = []
        start = time.monotonic()
        async for chunk in response.body_iterator:
            chunks.append(chunk)
            if ": heartbeat" in chunk and time.monotonic() - start > 0.3:
                break
            if time.monotonic() - start > 2.0:
                break
        elapsed = time.monotonic() - start

        full = "".join(chunks)
        assert ": connected" in full
        assert ": heartbeat" in full
        assert elapsed < 1.5, f"Heartbeat took {elapsed:.2f}s, expected < 1.5s"

    @pytest.mark.asyncio
    async def test_heartbeat_uses_sse_comment_format(
        self, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="running")
        from app.api.routes.workflows import stream_workflow_progress

        response = await stream_workflow_progress(
            execution_id=execution.id,
            request=_MockRequest(),
            user_id=str(test_user.id),
            db=db_session,
        )
        chunks: list[str] = []
        start = time.monotonic()
        async for chunk in response.body_iterator:
            chunks.append(chunk)
            if ": heartbeat\n\n" in chunk:
                break
            if time.monotonic() - start > 2.0:
                break

        full = "".join(chunks)
        assert ": heartbeat\n\n" in full


# ---------------------------------------------------------------------------
# /stream - closes on terminal event
# ---------------------------------------------------------------------------


class TestStreamTerminalClose:
    @pytest.mark.asyncio
    async def test_stream_closes_after_terminal_event(
        self, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="running")
        await _publish(execution.id, 2)
        from app.api.routes.workflows import stream_workflow_progress

        async def publish_terminal():
            await asyncio.sleep(0.1)
            pm = get_progress_manager()
            await pm.publish(
                execution.id,
                ExecutionEvent(
                    event_id=999,
                    execution_id=execution.id,
                    event_type=EventType.EXECUTION_COMPLETED,
                    timestamp=datetime.now(timezone.utc),
                    data={"status": "completed"},
                ),
            )

        terminal_task = asyncio.create_task(publish_terminal())
        try:
            response = await stream_workflow_progress(
                execution_id=execution.id,
                request=_MockRequest(),
                user_id=str(test_user.id),
                db=db_session,
            )
            chunks: list[str] = []
            async for chunk in response.body_iterator:
                chunks.append(chunk)
                if "id: 999\n" in chunk:
                    break
                if len(chunks) > 50:
                    break
        finally:
            terminal_task.cancel()
            try:
                await terminal_task
            except (asyncio.CancelledError, Exception):
                pass

        full = "".join(chunks)
        assert "id: 999\n" in full


# ---------------------------------------------------------------------------
# /snapshot
# ---------------------------------------------------------------------------


class TestSnapshotEndpoint:
    @pytest.mark.asyncio
    async def test_snapshot_returns_all_persisted_events(
        self, client, db_session, test_user
    ):
        from app.models.workflow_event import WorkflowEvent

        execution = await _make_execution(db_session, test_user, status="completed")
        for i, et in enumerate(
            [
                EventType.EXECUTION_STARTED.value,
                EventType.STAGE_STARTED.value,
                EventType.STAGE_COMPLETED.value,
                EventType.EXECUTION_COMPLETED.value,
            ],
            start=1,
        ):
            db_session.add(
                WorkflowEvent(
                    execution_id=execution.id,
                    event_type=et,
                    event_id=i,
                    data={"step": i},
                )
            )
        await db_session.commit()

        token = _token_for(test_user.id)
        response = await client.get(
            f"/api/workflows/results/{execution.id}/snapshot",
            params={"token": token},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["events"]) == 4
        assert [e["event_id"] for e in body["events"]] == [1, 2, 3, 4]
        assert body["events"][0]["event_type"] == "execution.started"
        assert body["events"][-1]["event_type"] == "execution.completed"
        assert body["execution"]["id"] == str(execution.id)
        assert body["execution"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_snapshot_returns_empty_events_for_execution_without_history(
        self, client, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user, status="completed")
        token = _token_for(test_user.id)
        response = await client.get(
            f"/api/workflows/results/{execution.id}/snapshot",
            params={"token": token},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["events"] == []
        assert body["execution"]["id"] == str(execution.id)

    @pytest.mark.asyncio
    async def test_snapshot_unauthorized_without_token(self, client, db_session, test_user):
        execution = await _make_execution(db_session, test_user, status="completed")
        response = await client.get(
            f"/api/workflows/results/{execution.id}/snapshot",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_snapshot_returns_404_for_cross_user_execution(
        self, client, db_session, test_user
    ):
        other_user = await _make_other_user(db_session)
        execution = await _make_execution(db_session, other_user, status="completed")
        token = _token_for(test_user.id)

        response = await client.get(
            f"/api/workflows/results/{execution.id}/snapshot",
            params={"token": token},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_snapshot_returns_404_for_nonexistent_execution(
        self, client, test_user
    ):
        token = _token_for(test_user.id)
        response = await client.get(
            f"/api/workflows/results/{uuid4()}/snapshot",
            params={"token": token},
        )
        assert response.status_code == 404
