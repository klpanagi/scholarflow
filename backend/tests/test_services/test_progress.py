"""Tests for the ProgressManager service.

All tests are ``unit_db`` — they exercise the in-memory queue and the
mocked Redis surface, never the real ``workflow_events`` table
(created in Task 1, running in parallel).  The DB persistence path is
verified by patching ``AsyncSessionLocal`` to fail gracefully, which
is the same code path used in production when the table is missing.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.services.progress import (
    EventType,
    ExecutionEvent,
    ProgressManager,
    get_progress_manager,
    progress_manager,
    reset_progress_manager,
)


pytestmark = pytest.mark.unit_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    execution_id: UUID,
    event_id: int,
    event_type: EventType = EventType.STAGE_STARTED,
    data: dict | None = None,
) -> ExecutionEvent:
    return ExecutionEvent(
        event_id=event_id,
        execution_id=execution_id,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        data=data or {"stage_id": f"stage-{event_id}"},
    )


def _new_manager() -> ProgressManager:
    """Fresh :class:`ProgressManager` with no Redis dependency."""
    return ProgressManager(redis_client=None)


# ---------------------------------------------------------------------------
# publish() + subscribe()
# ---------------------------------------------------------------------------


async def test_publish_subscribe_subscriber_receives_event():
    """publish() then subscribe() yields the published event."""
    pm = _new_manager()
    eid = uuid4()

    event = _make_event(eid, 1, EventType.STAGE_STARTED)
    await pm.publish(eid, event)

    received: list[ExecutionEvent] = []
    async for evt in pm.subscribe(eid):
        received.append(evt)
        if len(received) >= 1:
            break

    assert len(received) == 1
    assert received[0].event_id == 1
    assert received[0].event_type == EventType.STAGE_STARTED
    assert received[0].execution_id == eid


async def test_subscribe_replays_buffered_events_before_listening():
    """Late subscribers see events already in the bounded buffer."""
    pm = _new_manager()
    eid = uuid4()

    for i in range(1, 4):
        await pm.publish(eid, _make_event(eid, i))

    received: list[ExecutionEvent] = []
    async for evt in pm.subscribe(eid):
        received.append(evt)
        if len(received) >= 3:
            break

    assert [e.event_id for e in received] == [1, 2, 3]


async def test_subscribe_receives_events_published_after_subscribe():
    """Subscribers receive events that arrive after registration."""
    pm = _new_manager()
    eid = uuid4()

    received: list[ExecutionEvent] = []
    stop = asyncio.Event()

    async def consume() -> None:
        async for evt in pm.subscribe(eid):
            received.append(evt)
            if len(received) >= 2:
                stop.set()
                return

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0)  # let the consumer register

    await pm.publish(eid, _make_event(eid, 100))
    await pm.publish(eid, _make_event(eid, 101))

    await asyncio.wait_for(stop.wait(), timeout=1.0)
    await consumer

    assert [e.event_id for e in received[-2:]] == [100, 101]


# ---------------------------------------------------------------------------
# get_events() after_event_id
# ---------------------------------------------------------------------------


async def test_get_events_filters_by_after_event_id(monkeypatch):
    """get_events() returns only events strictly after ``after_event_id``."""
    pm = _new_manager()
    eid = uuid4()

    for i in range(1, 6):
        await pm.publish(eid, _make_event(eid, i))

    # Patch DB lookup to a no-op factory so the in-memory buffer is
    # the only source.  The lazy import inside get_events() re-binds
    # AsyncSessionLocal at call time, so a patched attribute is used.
    import app.core.database as db_mod
    monkeypatch.setattr(
        db_mod, "AsyncSessionLocal", MagicMock(side_effect=AssertionError("DB hit"))
    )

    events = await pm.get_events(eid, after_event_id=3)
    assert [e.event_id for e in events] == [4, 5]

    all_events = await pm.get_events(eid, after_event_id=0)
    assert [e.event_id for e in all_events] == [1, 2, 3, 4, 5]

    no_events = await pm.get_events(eid, after_event_id=5)
    assert no_events == []


# ---------------------------------------------------------------------------
# Queue overflow
# ---------------------------------------------------------------------------


async def test_queue_overflow_drops_oldest_and_emits_dropped(monkeypatch):
    """At 1001 events, the oldest is dropped and EVENTS_DROPPED is emitted."""
    pm = _new_manager()
    eid = uuid4()

    # Patch the DB/Redis fire-and-forget tasks to no-op so we can focus
    # on the in-memory queue behaviour.
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(pm, "_publish_to_redis", _noop)
    monkeypatch.setattr(pm, "_persist_to_db", _noop)

    # Open a subscription first so we can collect the dropped sentinel.
    received: list[ExecutionEvent] = []
    stop = asyncio.Event()

    async def consume() -> None:
        async for evt in pm.subscribe(eid):
            received.append(evt)
            if any(e.event_type == EventType.EVENTS_DROPPED for e in received):
                stop.set()
                return

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0)

    # Publish 1000 events (fills the buffer, no drops).
    for i in range(1, 1001):
        await pm.publish(eid, _make_event(eid, i))

    # The 1001st event triggers a drop.
    await pm.publish(eid, _make_event(eid, 1001))

    # Give the consumer a moment to observe the dropped event.
    try:
        await asyncio.wait_for(stop.wait(), timeout=1.0)
    finally:
        consumer.cancel()
        try:
            await consumer
        except (asyncio.CancelledError, Exception):
            pass

    buffer = pm._buffers[str(eid)]
    assert len(buffer) == 1000
    # The oldest event (id=1) must have been dropped.
    assert buffer[0].event_id == 2
    # The newest event (id=1001) is present.
    assert buffer[-1].event_id == 1001
    # An EVENTS_DROPPED sentinel was delivered to the subscriber.
    dropped = [e for e in received if e.event_type == EventType.EVENTS_DROPPED]
    assert dropped, "expected an EVENTS_DROPPED event in subscriber queue"
    assert dropped[0].data["count_dropped"] >= 1
    assert dropped[0].data["current_count"] == 1000


# ---------------------------------------------------------------------------
# Lifecycle: create_execution / complete_execution
# ---------------------------------------------------------------------------


async def test_create_execution_emits_execution_started(monkeypatch):
    pm = _new_manager()
    eid = uuid4()

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(pm, "_publish_to_redis", _noop)
    monkeypatch.setattr(pm, "_persist_to_db", _noop)

    await pm.create_execution(eid)

    buf = pm._buffers[str(eid)]
    assert len(buf) == 1
    assert buf[0].event_type == EventType.EXECUTION_STARTED
    assert buf[0].event_id == 1
    assert buf[0].execution_id == eid
    assert buf[0].data == {}


async def test_complete_execution_emits_terminal_events(monkeypatch):
    pm = _new_manager()
    eid = uuid4()

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(pm, "_publish_to_redis", _noop)
    monkeypatch.setattr(pm, "_persist_to_db", _noop)

    await pm.create_execution(eid)
    await pm.complete_execution(eid, status="completed")
    await pm.complete_execution(eid, status="failed")
    await pm.complete_execution(eid, status="cancelled")
    await pm.complete_execution(eid, status="error")

    types = [e.event_type for e in pm._buffers[str(eid)]]
    assert EventType.EXECUTION_STARTED in types
    assert EventType.EXECUTION_COMPLETED in types
    # "failed", "cancelled", and "error" all map to EXECUTION_FAILED.
    assert types.count(EventType.EXECUTION_FAILED) == 3
    ids = [e.event_id for e in pm._buffers[str(eid)]]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


async def test_create_complete_lifecycle_event_ids_monotonic(monkeypatch):
    pm = _new_manager()
    eid = uuid4()

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(pm, "_publish_to_redis", _noop)
    monkeypatch.setattr(pm, "_persist_to_db", _noop)

    await pm.create_execution(eid)
    await pm.publish(eid, _make_event(eid, 999))  # caller-supplied id
    await pm.complete_execution(eid)

    buf = pm._buffers[str(eid)]
    # create_execution → id=1, caller-supplied 999 sits in the middle,
    # complete_execution gets the next id from the manager's monotonic
    # counter (independent of any caller-supplied id).
    assert buf[0].event_id == 1
    assert buf[1].event_id == 999
    assert buf[2].event_id == 2
    # The manager's counter only sees create/complete (2 calls).
    assert pm._next_event_id[str(eid)] == 2


# ---------------------------------------------------------------------------
# Redis publish is attempted (fire-and-forget)
# ---------------------------------------------------------------------------


async def test_publish_invokes_redis_publish():
    """publish() schedules a redis publish for the live channel."""
    fake_redis = MagicMock()
    fake_redis.publish = AsyncMock()

    pm = ProgressManager(redis_client=fake_redis)
    eid = uuid4()

    # Monkeypatch DB persist to no-op.
    async def _noop(*args, **kwargs):
        return None
    pm._persist_to_db = _noop  # type: ignore[assignment]

    await pm.publish(eid, _make_event(eid, 1))

    # Fire-and-forget tasks may not have completed yet; wait briefly.
    for _ in range(20):
        if fake_redis.publish.await_count >= 1:
            break
        await asyncio.sleep(0.01)

    assert fake_redis.publish.await_count >= 1
    channel, payload = fake_redis.publish.call_args.args
    assert channel == f"workflow:events:{eid}"
    parsed = ExecutionEvent.from_json(payload)
    assert parsed.event_id == 1
    assert parsed.execution_id == eid


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------


def test_get_progress_manager_returns_singleton(monkeypatch):
    """get_progress_manager() returns the module-level singleton."""
    reset_progress_manager()

    fake_redis = MagicMock()
    monkeypatch.setattr(
        "app.core.database.redis_client", fake_redis, raising=False
    )

    pm1 = get_progress_manager()
    pm2 = get_progress_manager()
    assert pm1 is pm2
    assert pm1.redis is fake_redis

    reset_progress_manager()
