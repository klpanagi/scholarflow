"""ProgressManager — workflow execution event publishing and subscription.

Powers the live SSE stream for workflow executions. Decoupled from the
FastAPI request lifecycle so it can be called from background tasks,
agents, and HTTP handlers.

Local subscribers receive events via ``asyncio.Queue``; cross-process
consumers use the Redis channel ``workflow:events:{execution_id}``.
A bounded in-memory deque (max 1000) holds recent events for replay;
overflow drops the oldest and emits an ``EVENTS_DROPPED`` sentinel.

DB persistence to ``workflow_events`` is fire-and-forget — the in-memory
and Redis paths are authoritative for live consumers.

The module-level ``progress_manager`` singleton mirrors the
``_cancel_flags`` pattern in ``backend/app/api/routes/workflows.py:29-30``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Lifecycle events emitted during a workflow execution."""

    EXECUTION_STARTED = "execution.started"
    STAGE_STARTED = "stage.started"
    STAGE_COMPLETED = "stage.completed"
    NODE_STARTED = "node.started"
    NODE_COMPLETED = "node.completed"
    STRATEGY_ITERATION = "strategy.iteration"
    TOOL_CALL = "tool.call"
    TOOL_COMPLETE = "tool.complete"
    HEARTBEAT = "heartbeat"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
    EVENTS_DROPPED = "events.dropped"


class ExecutionEvent(BaseModel):
    """A single event in a workflow execution stream.

    Wire format (SSE)::

        id: <event_id>
        data: {"event_id": <int>, "execution_id": "<uuid>",
               "event_type": "<type>", "timestamp": "<iso8601>",
               "data": {...}}
    """

    event_id: int
    execution_id: UUID
    event_type: EventType
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True
        use_enum_values = False

    def to_json(self) -> str:
        return json.dumps(
            {
                "event_id": self.event_id,
                "execution_id": str(self.execution_id),
                "event_type": self.event_type.value,
                "timestamp": self.timestamp.isoformat(),
                "data": self.data,
            },
            default=str,
        )

    @classmethod
    def from_json(cls, payload: str | bytes) -> "ExecutionEvent":
        raw = json.loads(payload)
        return cls(
            event_id=raw["event_id"],
            execution_id=UUID(raw["execution_id"]),
            event_type=EventType(raw["event_type"]),
            timestamp=datetime.fromisoformat(raw["timestamp"]),
            data=raw.get("data") or {},
        )


_MAX_BUFFERED_EVENTS = 1000


class ProgressManager:
    """Coordinates workflow execution events for the SSE stream.

    Per-execution state: a bounded ``deque`` of recent events, a set of
    ``asyncio.Queue`` instances for local subscribers, and a monotonic
    ``event_id`` counter for events the manager constructs itself.
    """

    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client
        self._buffers: dict[str, deque[ExecutionEvent]] = {}
        self._subscribers: dict[str, set[asyncio.Queue[ExecutionEvent]]] = {}
        self._drop_counts: dict[str, int] = {}
        self._next_event_id: dict[str, int] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    @staticmethod
    def _channel(execution_id: UUID | str) -> str:
        return f"workflow:events:{execution_id}"

    @staticmethod
    def _key(execution_id: UUID | str) -> str:
        return str(execution_id)

    async def _lock_for(self, execution_id: str) -> asyncio.Lock:
        async with self._registry_lock:
            lock = self._locks.get(execution_id)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[execution_id] = lock
            return lock

    def _next_id(self, execution_id: str) -> int:
        # Caller must hold the per-execution lock.
        next_id = self._next_event_id.get(execution_id, 0) + 1
        self._next_event_id[execution_id] = next_id
        return next_id

    async def publish(
        self,
        execution_id: UUID | str,
        event: ExecutionEvent,
    ) -> None:
        """Publish ``event`` to local subscribers, Redis, and the DB.

        Local fan-out and bounded-buffer updates happen inline.
        Redis publishing and DB persistence are scheduled as background
        tasks so the publisher is never blocked by slow IO.
        """
        key = self._key(execution_id)
        lock = await self._lock_for(key)

        async with lock:
            buffer = self._buffers.get(key)
            if buffer is None:
                buffer = deque(maxlen=_MAX_BUFFERED_EVENTS)
                self._buffers[key] = buffer

            # Drop-oldest: the next append will evict the oldest element
            # if we're at capacity.  Track the drop so subscribers can
            # surface an EVENTS_DROPPED sentinel.
            drop_occurred = len(buffer) >= buffer.maxlen
            buffer.append(event)

            subscribers = self._subscribers.get(key)
            if subscribers:
                for queue in list(subscribers):
                    try:
                        queue.put_nowait(event)
                    except asyncio.QueueFull:  # pragma: no cover
                        logger.warning(
                            "Subscriber queue full for execution %s; dropping event %s",
                            key,
                            event.event_id,
                        )

            if drop_occurred:
                count = self._drop_counts.get(key, 0) + 1
                self._drop_counts[key] = count
                dropped_event = self._build_dropped_event(
                    execution_id, count, len(buffer)
                )
                if subscribers:
                    for queue in list(subscribers):
                        try:
                            queue.put_nowait(dropped_event)
                        except asyncio.QueueFull:  # pragma: no cover
                            pass
                asyncio.create_task(self._publish_to_redis(execution_id, dropped_event))
                asyncio.create_task(self._persist_to_db(execution_id, dropped_event))

        asyncio.create_task(self._publish_to_redis(execution_id, event))
        asyncio.create_task(self._persist_to_db(execution_id, event))

    def _build_dropped_event(
        self,
        execution_id: UUID | str,
        count: int,
        current: int,
    ) -> ExecutionEvent:
        return ExecutionEvent(
            # Negative sentinel so subscribers can distinguish meta-events
            # from real ones; the monotonic counter is not advanced.
            event_id=-count,
            execution_id=UUID(str(execution_id)) if not isinstance(execution_id, UUID) else execution_id,
            event_type=EventType.EVENTS_DROPPED,
            timestamp=datetime.now(timezone.utc),
            data={"count_dropped": count, "current_count": current},
        )

    async def _publish_to_redis(
        self,
        execution_id: UUID | str,
        event: ExecutionEvent,
    ) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.publish(self._channel(execution_id), event.to_json())
        except Exception as exc:  # pragma: no cover - network
            logger.warning(
                "Redis publish failed for execution %s event %s: %s",
                execution_id,
                event.event_id,
                exc,
            )

    async def _persist_to_db(
        self,
        execution_id: UUID | str,
        event: ExecutionEvent,
    ) -> None:
        """Persist the event to the ``workflow_events`` table.

        Uses :class:`AsyncSessionLocal` so it works from background
        tasks (no FastAPI request scope).  Failures are logged and
        swallowed — in-memory and Redis paths remain authoritative
        for live consumers.
        """
        try:
            # Lazy imports keep the module import-safe while the
            # workflow_events model is being added in a parallel task.
            from app.core.database import AsyncSessionLocal
            from app.models.workflow_event import WorkflowEvent  # type: ignore[import-not-found]

            exec_uuid = (
                execution_id
                if isinstance(execution_id, UUID)
                else UUID(str(execution_id))
            )

            async with AsyncSessionLocal() as session:
                session.add(
                    WorkflowEvent(
                        execution_id=exec_uuid,
                        event_type=event.event_type.value,
                        event_id=event.event_id,
                        timestamp=event.timestamp,
                        data=event.data,
                    )
                )
                await session.commit()
        except ImportError:
            # workflow_events model not yet migrated; skip silently.
            logger.debug(
                "workflow_events model not yet available; skipping DB persist for %s",
                execution_id,
            )
        except Exception as exc:  # pragma: no cover - DB unavailable
            logger.warning(
                "Failed to persist event %s for execution %s: %s",
                event.event_id,
                execution_id,
                exc,
            )

    async def subscribe(
        self,
        execution_id: UUID | str,
    ) -> AsyncIterator[ExecutionEvent]:
        """Yield events for ``execution_id`` as an async iterator.

        Replays any events currently in the in-memory buffer, then
        registers a local queue and yields new events as they are
        published.  On exit, the queue is unregistered.
        """
        key = self._key(execution_id)
        queue: asyncio.Queue[ExecutionEvent] = asyncio.Queue()
        lock = await self._lock_for(key)

        async with lock:
            subscribers = self._subscribers.setdefault(key, set())
            subscribers.add(queue)
            # Snapshot the buffer under the lock so we don't miss an
            # event published between ``list()`` and registration.
            buffer = self._buffers.get(key)
            replay = list(buffer) if buffer else []

        for event in replay:
            yield event

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with lock:
                current = self._subscribers.get(key)
                if current is not None:
                    current.discard(queue)
                    if not current:
                        self._subscribers.pop(key, None)

    async def get_events(
        self,
        execution_id: UUID | str,
        after_event_id: int = 0,
    ) -> list[ExecutionEvent]:
        """Return events for ``execution_id`` strictly after ``after_event_id``.

        Merges the in-memory buffer (recent) with the ``workflow_events``
        table (durable) so the SSE endpoint can resume a stream from
        the ``Last-Event-ID`` header.  Results are deduplicated and
        sorted by ``event_id`` ascending.
        """
        key = self._key(execution_id)
        events: dict[int, ExecutionEvent] = {}
        lock = await self._lock_for(key)

        async with lock:
            buffer = self._buffers.get(key)
            if buffer:
                for event in buffer:
                    if event.event_id > after_event_id:
                        events[event.event_id] = event

        try:
            from app.core.database import AsyncSessionLocal
            from app.models.workflow_event import WorkflowEvent  # type: ignore[import-not-found]
            from sqlalchemy import select

            exec_uuid = (
                execution_id
                if isinstance(execution_id, UUID)
                else UUID(str(execution_id))
            )

            async with AsyncSessionLocal() as session:
                stmt = (
                    select(WorkflowEvent)
                    .where(
                        WorkflowEvent.execution_id == exec_uuid,
                        WorkflowEvent.event_id > after_event_id,
                    )
                    .order_by(WorkflowEvent.event_id)
                )
                result = await session.execute(stmt)
                for row in result.scalars():
                    event = ExecutionEvent(
                        event_id=row.event_id,
                        execution_id=row.execution_id,
                        event_type=EventType(row.event_type),
                        timestamp=row.timestamp,
                        data=row.data or {},
                    )
                    events[event.event_id] = event
        except ImportError:
            logger.debug(
                "workflow_events model not yet available; replay from buffer only"
            )
        except Exception as exc:  # pragma: no cover - DB unavailable
            logger.warning("Failed to read events from DB: %s", exc)

        return [events[k] for k in sorted(events)]

    async def create_execution(self, execution_id: UUID | str) -> None:
        """Emit an ``EXECUTION_STARTED`` event for ``execution_id``."""
        key = self._key(execution_id)
        exec_uuid = (
            execution_id
            if isinstance(execution_id, UUID)
            else UUID(str(execution_id))
        )
        event = ExecutionEvent(
            event_id=self._next_id(key),
            execution_id=exec_uuid,
            event_type=EventType.EXECUTION_STARTED,
            timestamp=datetime.now(timezone.utc),
            data={},
        )
        await self.publish(execution_id, event)

    async def complete_execution(
        self,
        execution_id: UUID | str,
        status: str = "completed",
    ) -> None:
        """Emit a terminal event (``completed``/``failed``/``cancelled``)."""
        key = self._key(execution_id)
        exec_uuid = (
            execution_id
            if isinstance(execution_id, UUID)
            else UUID(str(execution_id))
        )
        normalized = (status or "completed").lower()
        if normalized in ("failed", "error", "cancelled", "canceled"):
            event_type = EventType.EXECUTION_FAILED
        else:
            event_type = EventType.EXECUTION_COMPLETED

        event = ExecutionEvent(
            event_id=self._next_id(key),
            execution_id=exec_uuid,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            data={"status": normalized},
        )
        await self.publish(execution_id, event)

    def reset(self) -> None:
        """Drop all in-memory state.  Test-only."""
        self._buffers.clear()
        self._subscribers.clear()
        self._drop_counts.clear()
        self._next_event_id.clear()
        self._locks.clear()


progress_manager: ProgressManager | None = None


def get_progress_manager() -> ProgressManager:
    """Return the lazily-initialised singleton :class:`ProgressManager`."""
    global progress_manager
    if progress_manager is None:
        # Import inside the factory to avoid a circular import at module
        # load time (database imports settings).
        from app.core.database import redis_client

        progress_manager = ProgressManager(redis_client=redis_client)
    return progress_manager


def reset_progress_manager() -> None:
    """Reset the singleton and clear its in-memory state.  Test-only."""
    global progress_manager
    if progress_manager is not None:
        progress_manager.reset()
    progress_manager = None


__all__ = [
    "EventType",
    "ExecutionEvent",
    "ProgressManager",
    "get_progress_manager",
    "progress_manager",
    "reset_progress_manager",
]
