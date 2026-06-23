"""Tests for the WorkflowEvent model and the workflow_events table.

These tests exercise persistence and referential integrity of
``WorkflowEvent`` rows against the real test PostgreSQL.
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import WorkflowEvent, WorkflowExecution
from app.schemas import (
    ExecutionEvent,
    WorkflowEventResponse,
    WorkflowSnapshotResponse,
)


async def _make_execution(db_session, test_user) -> WorkflowExecution:
    """Create and commit a :class:`WorkflowExecution` row for ``test_user``."""
    execution = WorkflowExecution(
        user_id=test_user.id,
        workflow_id="scholarflow",
        workflow_name="ScholarFlow Test Run",
        input_text="Test input",
        stages=[{"stage_id": "researcher", "status": "pending"}],
        status="running",
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)
    return execution


class TestWorkflowEventPersistence:
    """Insert/read roundtrip for the ``WorkflowEvent`` model."""

    async def test_create_workflow_event_is_retrievable_by_execution_id(
        self, db_session, test_user
    ):
        execution = await _make_execution(db_session, test_user)

        event = WorkflowEvent(
            execution_id=execution.id,
            event_type="stage.started",
            event_id=1,
            data={"stage_id": "researcher", "agent_role": "researcher"},
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        result = await db_session.execute(
            select(WorkflowEvent).where(WorkflowEvent.execution_id == execution.id)
        )
        events = result.scalars().all()

        assert len(events) == 1
        fetched = events[0]
        assert fetched.id == event.id
        assert isinstance(fetched.id, uuid.UUID)
        assert fetched.id.version == 4
        assert fetched.execution_id == execution.id
        assert fetched.event_type == "stage.started"
        assert fetched.event_id == 1
        assert fetched.data == {"stage_id": "researcher", "agent_role": "researcher"}
        assert fetched.timestamp is not None

    async def test_event_id_monotonic_within_execution(self, db_session, test_user):
        """Separate inserts increment event_id per execution.

        The publisher assigns event_id sequentially; this test verifies
        that the column does not auto-increment at the DB level and that
        distinct inserts can carry different values that round-trip
        correctly.
        """
        execution = await _make_execution(db_session, test_user)

        for event_id in (1, 2, 3):
            db_session.add(
                WorkflowEvent(
                    execution_id=execution.id,
                    event_type="node.completed",
                    event_id=event_id,
                    data={"node_name": f"node-{event_id}"},
                )
            )
        await db_session.commit()

        result = await db_session.execute(
            select(WorkflowEvent.event_id)
            .where(WorkflowEvent.execution_id == execution.id)
            .order_by(WorkflowEvent.event_id)
        )
        event_ids = [row[0] for row in result.all()]

        assert event_ids == [1, 2, 3]

    async def test_event_id_monotonic_independent_per_execution(
        self, db_session, test_user
    ):
        """Two executions each maintain their own event_id sequence."""
        execution_a = await _make_execution(db_session, test_user)
        execution_b = await _make_execution(db_session, test_user)

        db_session.add_all(
            [
                WorkflowEvent(
                    execution_id=execution_a.id,
                    event_type="execution.started",
                    event_id=1,
                    data={},
                ),
                WorkflowEvent(
                    execution_id=execution_b.id,
                    event_type="execution.started",
                    event_id=1,
                    data={},
                ),
            ]
        )
        await db_session.commit()

        result_a = await db_session.execute(
            select(WorkflowEvent.event_id).where(
                WorkflowEvent.execution_id == execution_a.id
            )
        )
        result_b = await db_session.execute(
            select(WorkflowEvent.event_id).where(
                WorkflowEvent.execution_id == execution_b.id
            )
        )
        assert [row[0] for row in result_a.all()] == [1]
        assert [row[0] for row in result_b.all()] == [1]


class TestWorkflowEventReferentialIntegrity:
    """FK and uniqueness constraints enforced by the database."""

    async def test_unique_constraint_on_execution_event_id(
        self, db_session, test_user
    ):
        """Inserting a duplicate (execution_id, event_id) is rejected."""
        execution = await _make_execution(db_session, test_user)

        db_session.add(
            WorkflowEvent(
                execution_id=execution.id,
                event_type="stage.started",
                event_id=1,
                data={},
            )
        )
        await db_session.commit()

        db_session.add(
            WorkflowEvent(
                execution_id=execution.id,
                event_type="stage.completed",
                event_id=1,
                data={},
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_execution_id_fk_cascade_on_delete(self, db_session, test_user):
        """Deleting a WorkflowExecution removes all of its events."""
        execution = await _make_execution(db_session, test_user)

        for event_id in (1, 2, 3):
            db_session.add(
                WorkflowEvent(
                    execution_id=execution.id,
                    event_type="node.completed",
                    event_id=event_id,
                    data={},
                )
            )
        await db_session.commit()

        count_before = await db_session.execute(
            select(func.count()).select_from(WorkflowEvent).where(
                WorkflowEvent.execution_id == execution.id
            )
        )
        assert count_before.scalar_one() == 3

        await db_session.delete(execution)
        await db_session.commit()

        count_after = await db_session.execute(
            select(func.count()).select_from(WorkflowEvent).where(
                WorkflowEvent.execution_id == execution.id
            )
        )
        assert count_after.scalar_one() == 0


class TestWorkflowEventTypeCategorization:
    """The full SSE event taxonomy is representable in the column."""

    @pytest.mark.parametrize(
        "event_type",
        [
            "execution.started",
            "stage.started",
            "node.started",
            "node.completed",
            "strategy.iteration",
            "tool.call",
            "tool.complete",
            "stage.completed",
            "execution.completed",
            "execution.failed",
            "execution.cancelled",
            "heartbeat",
            "events.dropped",
        ],
    )
    async def test_event_type_round_trips(
        self, db_session, test_user, event_type
    ):
        execution = await _make_execution(db_session, test_user)

        event = WorkflowEvent(
            execution_id=execution.id,
            event_type=event_type,
            event_id=1,
            data={"event_type": event_type},
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        assert event.event_type == event_type

    async def test_data_column_accepts_nested_json(self, db_session, test_user):
        """The ``data`` JSONB column stores arbitrary structured payloads."""
        execution = await _make_execution(db_session, test_user)
        payload = {
            "stage_id": "researcher",
            "agent_role": "researcher",
            "agent_name": "Test Researcher",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "nested": {"deep": {"key": "value"}},
            "list": [1, 2, 3],
        }

        event = WorkflowEvent(
            execution_id=execution.id,
            event_type="stage.completed",
            event_id=1,
            data=payload,
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        assert event.data == payload

    async def test_data_column_default_is_empty_dict(self, db_session, test_user):
        """Omitting ``data`` yields an empty dict (server default ``{}``)."""
        execution = await _make_execution(db_session, test_user)

        event = WorkflowEvent(
            execution_id=execution.id,
            event_type="heartbeat",
            event_id=1,
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        assert event.data == {}


class TestWorkflowEventSchemas:
    """Pydantic schemas serialize and validate ``WorkflowEvent`` rows."""

    @pytest.mark.unit_db
    def test_execution_event_defaults(self):
        event = ExecutionEvent(
            event_id=1,
            execution_id=uuid.uuid4(),
            event_type="stage.started",
        )
        assert event.data == {}
        assert event.timestamp is not None
        assert event.event_type == "stage.started"

    @pytest.mark.unit_db
    def test_workflow_event_response_from_attributes(self):
        response = WorkflowEventResponse(
            id=uuid.uuid4(),
            execution_id=uuid.uuid4(),
            event_type="node.completed",
            event_id=42,
            timestamp=datetime.now(timezone.utc),
            data={"node_name": "scholar"},
        )
        assert response.event_id == 42
        assert response.data == {"node_name": "scholar"}

    @pytest.mark.unit_db
    def test_workflow_snapshot_response_shape(self):
        execution_id = uuid.uuid4()
        snapshot = WorkflowSnapshotResponse(
            execution_id=execution_id,
            events=[],
            last_event_id=0,
        )
        assert snapshot.execution_id == execution_id
        assert snapshot.events == []
        assert snapshot.last_event_id == 0
