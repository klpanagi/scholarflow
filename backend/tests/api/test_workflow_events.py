"""Tests for workflow event publishing (Task 7).

Verifies the four lifecycle-event contracts that the workflow runner must
satisfy for the live SSE stream (Task 8) and the post-hoc snapshot endpoint:

- Each stage publishes ``STAGE_STARTED`` and ``STAGE_COMPLETED`` with the
  expected data fields.
- Events are persisted to the ``workflow_events`` table (Task 1) so the
  SSE ``Last-Event-ID`` replay path can resume a stream.
- Cancellation publishes a terminal event with status ``"cancelled"``.
- A stage that raises publishes a terminal ``EXECUTION_FAILED`` event with
  the error info.

All tests use ``unit_db`` to avoid the session-scoped
``db_engine`` fixture, which is broken in pytest-asyncio 1.4.0 in this
environment. The DB-persistence test creates its own engine against
``TEST_DATABASE_URL`` (port 15432) and manages its own transaction.
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import Base
from app.models import AgentRole, User, WorkflowExecution
from app.models.workflow_event import WorkflowEvent
from app.services.progress import (
    EventType,
    ProgressManager,
    get_progress_manager,
    reset_progress_manager,
)


pytestmark = pytest.mark.unit_db


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:15432/academic_pal_test",
)


# Paper-review workflow stage IDs (must match WORKFLOW_DEFINITIONS in
# app.api.routes.workflows).
STAGE_IDS = [
    "search-related-work",
    "review-paper",
    "debate-review",
    "paper-review-writer",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(role: AgentRole | None = None) -> MagicMock:
    config = MagicMock()
    config.name = "test-agent"
    config.role = role or AgentRole.RESEARCHER
    config.model = "test-model"
    config.provider = "test-provider"
    config.strategy = MagicMock(value="direct")
    config.skills = []
    config.system_prompt = "Test system prompt"
    config.temperature = 0.7
    config.max_tokens = 4096
    config.variant = None
    return config


def _make_agent_result(
    output: str = "Agent output.",
    context: dict | None = None,
    usage: dict | None = None,
) -> dict:
    return {
        "output": output,
        "context": context or {},
        "metadata": {
            "usage": usage
            or {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        },
    }


class _PublishSpy:
    """Context manager that wraps ``ProgressManager.publish`` to record events.

    Use as ``with _PublishSpy(pm) as captured:``.  The wrapper delegates
    to the real ``publish`` so the in-memory buffer and the fire-and-forget
    DB tasks still run; we only observe what flows through.
    """

    def __init__(self, pm: ProgressManager) -> None:
        self.pm = pm
        self.captured: list[tuple[EventType, dict]] = []
        self._original = pm.publish

    def __enter__(self):
        async def spy(execution_id, event):
            self.captured.append((event.event_type, event.data))
            await self._original(execution_id, event)

        self.pm.publish = spy
        return self.captured

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pm.publish = self._original
        return False


def _make_workflow_session(execution_id: UUID):
    """Build a mock session/context-manager pair used by ``AsyncSessionLocal``.

    The mock stores whatever the workflow writes to
    ``execution.stages`` and ``execution.status`` so the test can assert on
    the final state.  We avoid mocking the per-statement execute calls
    too aggressively — only the ``scalar_one_or_none`` for fetching the
    ``WorkflowExecution`` row matters for the progress tests.
    """
    mock_execution = MagicMock()
    mock_execution.id = execution_id
    mock_execution.stages = []
    mock_execution.status = "pending"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_execution

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session
    mock_session_cm.__aexit__.return_value = False
    return mock_session, mock_session_cm, mock_execution


def _patch_workflow_deps(
    mock_session_cm,
    mock_session,
    config_map: dict[str, MagicMock],
    mock_agents: list[MagicMock],
    cancel_flag: dict[str, bool] | None = None,
):
    """Return a stack of patches to apply around ``_run_workflow_background``."""
    agent_iter = iter(mock_agents)

    def create_agent_side_effect(*_args, **_kwargs):
        return next(agent_iter)

    async def mock_get_config(_db, _user_id, config_id):
        return config_map.get(str(config_id))

    patches = [
        patch("app.api.routes.workflows.AsyncSessionLocal", return_value=mock_session_cm),
        patch("app.api.routes.workflows._get_user_config_by_id", side_effect=mock_get_config),
        patch("app.api.routes.workflows.create_agent", side_effect=create_agent_side_effect),
        patch(
            "app.api.routes.workflows.fetch_model_pricing",
            new_callable=AsyncMock,
            return_value={},
        ),
        patch("app.api.routes.workflows.calculate_cost", return_value=0.0),
        patch("app.api.routes.workflows.model_supports_pdf", return_value=False),
        patch(
            "app.api.routes.workflows.evaluate_rubric",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.api.routes.workflows._build_stage_context",
            side_effect=lambda orig, _find: orig,
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ]
    return patches


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset module-level singletons so tests don't pollute each other."""
    reset_progress_manager()
    from app.api.routes.workflows import _cancel_flags
    _cancel_flags.clear()
    yield
    reset_progress_manager()
    _cancel_flags.clear()


@pytest_asyncio.fixture
async def fresh_db_engine():
    """Function-scoped async engine against the test DB.

    Truncates data tables before yielding so tests start from a clean
    schema.  The conftest's session-scoped ``db_engine`` fixture is
    broken under pytest-asyncio 1.4.0 in this environment, so each test
    manages its own connection.
    """
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.begin() as conn:
        # Truncate data tables in dependency order.  RESTART IDENTITY
        # CASCADE handles FK ordering automatically.
        await conn.execute(
            text(
                "TRUNCATE TABLE workflow_events, workflow_executions, "
                "agent_configs, users RESTART IDENTITY CASCADE"
            )
        )
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(fresh_db_engine):
    return async_sessionmaker(
        fresh_db_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest_asyncio.fixture
async def test_execution(session_factory):
    """Insert a User + WorkflowExecution row in a single session.

    Combined because the FK on ``workflow_executions.user_id`` requires
    the parent row to be visible; with detached instances across two
    short-lived sessions, SQLAlchemy's refresh can fail in confusing
    ways under asyncpg.
    """
    async with session_factory() as session:
        user = User(
            email="events-test@example.com",
            name="Events Test",
            hashed_password="x",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        exec_row = WorkflowExecution(
            id=uuid4(),
            user_id=user.id,
            workflow_id="paper-review",
            workflow_name="Paper Review Pipeline",
            input_text="Test input",
            agent_assignments={},
            stages=[],
        )
        session.add(exec_row)
        await session.commit()

        exec_id = str(exec_row.id)
        user_id = str(user.id)
        return exec_id, user_id


# ---------------------------------------------------------------------------
# Test: STAGE_STARTED + STAGE_COMPLETED per stage
# ---------------------------------------------------------------------------


class TestRunningWorkflowPublishesStageEvents:
    @pytest.mark.asyncio
    async def test_running_workflow_publishes_stage_started_and_completed_for_each_stage(
        self,
    ):
        """All 4 stages each publish a STAGE_STARTED and STAGE_COMPLETED event.

        Uses the in-memory replay buffer (``_buffers``) of the singleton
        ``ProgressManager`` to avoid a real DB.  The buffer is consulted
        via the manager's ``_buffers`` dict directly, which is the same
        storage the SSE endpoint reads from.
        """
        mock_agents = [
            MagicMock(
                run=AsyncMock(return_value=_make_agent_result(f"Stage {i + 1} done."))
            )
            for i in range(4)
        ]
        assignments = {sid: str(uuid4()) for sid in STAGE_IDS}
        config_map = {cid: _make_config() for cid in assignments.values()}

        execution_id = str(uuid4())
        mock_session, mock_session_cm, mock_execution = _make_workflow_session(
            UUID(execution_id)
        )
        mock_execution.id = UUID(execution_id)

        patches = _patch_workflow_deps(
            mock_session_cm, mock_session, config_map, mock_agents
        )

        with _PublishSpy(get_progress_manager()) as captured:
            for p in patches:
                p.start()
            try:
                from app.api.routes.workflows import _run_workflow_background

                await _run_workflow_background(
                    execution_id=execution_id,
                    user_id="test-user",
                    workflow_id="paper-review",
                    original_context="Test paper content",
                    pdf_bytes=None,
                    paper_s2_id=None,
                    topic_query="test query",
                    agent_assignments=assignments,
                    paper_content=None,
                    rubric_standard="general",
                )
            finally:
                for p in reversed(patches):
                    p.stop()

        started = [d for t, d in captured if t == EventType.STAGE_STARTED]
        completed = [d for t, d in captured if t == EventType.STAGE_COMPLETED]

        assert len(started) == 4, (
            f"Expected 4 STAGE_STARTED events (one per stage); got {len(started)}"
        )
        assert len(completed) == 4, (
            f"Expected 4 STAGE_COMPLETED events (one per stage); got {len(completed)}"
        )

        for idx, data in enumerate(started):
            assert data["stage_id"] == STAGE_IDS[idx]
            assert data["stage_index"] == idx
            assert data["agent_role"], f"agent_role missing for stage {idx}"
            assert "agent_name" in data

        for idx, data in enumerate(completed):
            assert data["stage_id"] == STAGE_IDS[idx]
            assert data["stage_index"] == idx
            assert data["status"] == "completed"
            assert data["duration_ms"] >= 0
            assert data["usage"]["total_tokens"] == 150

    @pytest.mark.asyncio
    async def test_run_stage_passes_progress_manager_and_execution_id_to_agent(self):
        """``_run_stage`` forwards ``progress_manager`` and ``execution_id`` to ``agent.run()``."""
        execution_id = str(uuid4())
        mock_agent = MagicMock(run=AsyncMock(return_value=_make_agent_result("done.")))
        config = _make_config()
        mock_session, mock_session_cm, _ = _make_workflow_session(UUID(execution_id))
        mock_execution_id = UUID(execution_id)

        from app.models.workflow_event import WorkflowEvent  # noqa: F401  ensure importable

        with (
            patch(
                "app.api.routes.workflows._get_user_config_by_id",
                new_callable=AsyncMock,
                return_value=config,
            ),
            patch("app.api.routes.workflows.create_agent", return_value=mock_agent),
            patch(
                "app.api.routes.workflows.fetch_model_pricing",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("app.api.routes.workflows.calculate_cost", return_value=0.0),
            patch("app.api.routes.workflows.model_supports_pdf", return_value=False),
            patch(
                "app.api.routes.workflows.evaluate_rubric",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            from app.api.routes.workflows import _run_stage

            pm = get_progress_manager()
            await pm.create_execution(mock_execution_id)

            await _run_stage(
                db=mock_session,
                user_id="user1",
                stage_def={
                    "id": "search",
                    "role": AgentRole.RESEARCHER.value,
                    "task_template": "Search: {input}",
                },
                context="paper content",
                config_id=uuid4(),
                progress_manager=pm,
                execution_id=mock_execution_id,
            )

        kwargs = mock_agent.run.call_args.kwargs
        assert kwargs.get("progress_manager") is pm, (
            "agent.run() must receive the same ProgressManager singleton"
        )
        assert kwargs.get("execution_id") == mock_execution_id, (
            "agent.run() must receive the execution_id for downstream events"
        )


# ---------------------------------------------------------------------------
# Test: events persisted in workflow_events table
# ---------------------------------------------------------------------------


class TestEventsPersistedInDB:
    @pytest.mark.asyncio
    async def test_completed_workflow_events_persisted_in_db(
        self, test_execution, session_factory
    ):
        """Each event published during the workflow lands in ``workflow_events``.

        The manager persists via fire-and-forget ``asyncio.create_task``s
        (see progress.py:publish → _persist_to_db).  We patch
        ``AsyncSessionLocal`` to the test session's sessionmaker and
        await the tracked tasks at the end so the writes are flushed
        before we query.
        """
        execution_id_str, user_id_str = test_execution
        execution_id = UUID(execution_id_str)
        mock_agents = [
            MagicMock(
                run=AsyncMock(return_value=_make_agent_result(f"Stage {i + 1}."))
            )
            for i in range(4)
        ]
        assignments = {sid: str(uuid4()) for sid in STAGE_IDS}
        config_map = {cid: _make_config() for cid in assignments.values()}

        mock_session, mock_session_cm, mock_execution_obj = _make_workflow_session(
            execution_id
        )
        mock_execution_obj.id = execution_id

        tracked_tasks: list[asyncio.Task] = []
        original_create_task = asyncio.create_task

        def tracking_create_task(coro, *args, **kwargs):
            task = original_create_task(coro, *args, **kwargs)
            tracked_tasks.append(task)
            return task

        class FakeAsyncSessionLocal:
            def __call__(self):
                return session_factory()

        # Capture each event the manager sees, in the order it's seen.
        published_events: list[tuple[str, dict]] = []
        pm = get_progress_manager()
        original_publish = pm.publish

        async def capture_publish(execution_id, event):
            published_events.append((event.event_type.value, dict(event.data)))
            await original_publish(execution_id, event)

        patches = _patch_workflow_deps(
            mock_session_cm, mock_session, config_map, mock_agents
        )

        # The progress module imports AsyncSessionLocal from
        # app.core.database at function scope; patch that symbol so the
        # fire-and-forget DB writes go to the test DB (port 15432).
        all_patches = [
            patch("app.api.routes.workflows.AsyncSessionLocal", FakeAsyncSessionLocal()),
            patch("app.core.database.AsyncSessionLocal", FakeAsyncSessionLocal()),
            patch("app.services.progress.asyncio.create_task", tracking_create_task),
            patch.object(pm, "publish", capture_publish),
            *patches,
        ]
        for p in all_patches:
            p.start()
        try:
            from app.api.routes.workflows import _run_workflow_background

            await _run_workflow_background(
                execution_id=execution_id_str,
                user_id=user_id_str,
                workflow_id="paper-review",
                original_context="Test paper content",
                pdf_bytes=None,
                paper_s2_id=None,
                topic_query="test query",
                agent_assignments=assignments,
                paper_content=None,
                rubric_standard="general",
            )

            # Give the fire-and-forget DB tasks a chance to run inside
            # the same event loop.  They were created above so they are
            # scheduled but not yet complete.
            await asyncio.gather(*tracked_tasks, return_exceptions=True)
        finally:
            for p in reversed(all_patches):
                p.stop()

        async with session_factory() as session:
            stmt = select(WorkflowEvent).where(
                WorkflowEvent.execution_id == execution_id
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        from collections import Counter

        type_counts = Counter(r.event_type for r in rows)
        assert type_counts["execution.started"] == 1
        assert type_counts["stage.started"] == 4
        assert type_counts["stage.completed"] == 4
        assert type_counts["execution.completed"] == 1
        assert len(rows) == 10, (
            f"Expected 10 events (1 execution.started + 4 stage.started + "
            f"4 stage.completed + 1 execution.completed); got {len(rows)}"
        )


# ---------------------------------------------------------------------------
# Test: cancelled workflow publishes terminal event
# ---------------------------------------------------------------------------


class TestCancelledWorkflow:
    @pytest.mark.asyncio
    async def test_cancelled_workflow_publishes_terminal_event(self):
        """Setting ``_cancel_flags[execution_id] = True`` publishes EXECUTION_FAILED with status=cancelled.

        The ``complete_execution`` helper normalizes "cancelled" into an
        ``EXECUTION_FAILED`` event whose ``data.status`` is
        ``"cancelled"`` (see progress.py:391-416 — there's no separate
        ``EXECUTION_CANCELLED`` event type in the current taxonomy).
        """
        execution_id = str(uuid4())
        mock_agents = [
            MagicMock(run=AsyncMock(return_value=_make_agent_result("ok")))
            for _ in range(4)
        ]
        assignments = {sid: str(uuid4()) for sid in STAGE_IDS}
        config_map = {cid: _make_config() for cid in assignments.values()}

        mock_session, mock_session_cm, mock_execution = _make_workflow_session(
            UUID(execution_id)
        )
        mock_execution.id = UUID(execution_id)

        # Pre-set the cancel flag so the loop bails before the first stage.
        from app.api.routes.workflows import _cancel_flags

        _cancel_flags[execution_id] = True

        patches = _patch_workflow_deps(
            mock_session_cm, mock_session, config_map, mock_agents
        )

        with _PublishSpy(get_progress_manager()) as captured:
            for p in patches:
                p.start()
            try:
                from app.api.routes.workflows import _run_workflow_background

                await _run_workflow_background(
                    execution_id=execution_id,
                    user_id="test-user",
                    workflow_id="paper-review",
                    original_context="Test paper content",
                    pdf_bytes=None,
                    paper_s2_id=None,
                    topic_query="test query",
                    agent_assignments=assignments,
                    paper_content=None,
                    rubric_standard="general",
                )
            finally:
                for p in reversed(patches):
                    p.stop()

        terminal = [
            d for t, d in captured if t == EventType.EXECUTION_FAILED
        ]
        assert len(terminal) == 1, (
            f"Expected exactly 1 terminal EXECUTION_FAILED event for cancellation; "
            f"got {len(terminal)}"
        )
        assert terminal[0]["status"] == "cancelled"

        # No STAGE_STARTED events should have been published because the
        # loop bails before reaching the stage body.
        started = [d for t, d in captured if t == EventType.STAGE_STARTED]
        assert started == [], (
            f"Expected 0 STAGE_STARTED events when cancelled before stage 0; "
            f"got {len(started)}"
        )


# ---------------------------------------------------------------------------
# Test: failed workflow publishes EXECUTION_FAILED with error info
# ---------------------------------------------------------------------------


class TestFailedWorkflow:
    @pytest.mark.asyncio
    async def test_failed_workflow_publishes_execution_failed_with_error(self):
        """When ``_run_stage`` itself raises, the workflow publishes EXECUTION_FAILED.

        ``_run_stage`` swallows agent exceptions via its retry-on-429
        block and returns ``status="error"`` instead of raising, so to
        exercise the outer try/except we patch ``_run_stage`` to raise
        directly.  This is the path that fires for catastrophic failures
        (DB outage, programming error in the stage wiring, etc.).
        """
        execution_id = str(uuid4())
        boom = RuntimeError("simulated stage failure")

        assignments = {sid: str(uuid4()) for sid in STAGE_IDS}
        config_map = {cid: _make_config() for cid in assignments.values()}

        mock_session, mock_session_cm, mock_execution = _make_workflow_session(
            UUID(execution_id)
        )
        mock_execution.id = UUID(execution_id)

        # Patch _run_stage to raise unconditionally so the workflow's
        # outer try/except fires.
        run_stage_patch = patch(
            "app.api.routes.workflows._run_stage",
            new_callable=AsyncMock,
            side_effect=boom,
        )

        patches = _patch_workflow_deps(
            mock_session_cm, mock_session, config_map, []
        )

        with _PublishSpy(get_progress_manager()) as captured:
            for p in [*patches, run_stage_patch]:
                p.start()
            try:
                from app.api.routes.workflows import _run_workflow_background

                # The function must NOT raise to the caller; failures are
                # caught and recorded as a terminal event with status="failed".
                await _run_workflow_background(
                    execution_id=execution_id,
                    user_id="test-user",
                    workflow_id="paper-review",
                    original_context="Test paper content",
                    pdf_bytes=None,
                    paper_s2_id=None,
                    topic_query="test query",
                    agent_assignments=assignments,
                    paper_content=None,
                    rubric_standard="general",
                )
            finally:
                for p in reversed([*patches, run_stage_patch]):
                    p.stop()

        # STAGE_COMPLETED with status="failed" was published for the failing
        # stage before the exception propagated.
        stage_completed = [
            d for t, d in captured if t == EventType.STAGE_COMPLETED
        ]
        assert any(
            d["status"] == "failed" and "error" in d for d in stage_completed
        ), (
            f"Expected at least one STAGE_COMPLETED with status=failed and an "
            f"`error` field; got {stage_completed}"
        )

        # Terminal EXECUTION_FAILED event for the workflow itself.
        terminal = [
            d for t, d in captured if t == EventType.EXECUTION_FAILED
        ]
        assert len(terminal) == 1
        assert terminal[0]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_run_stage_without_progress_manager_is_backward_compatible(self):
        """Calling ``_run_stage`` without progress_manager still works (old callers)."""
        mock_agent = MagicMock(run=AsyncMock(return_value=_make_agent_result("ok")))
        config = _make_config()
        mock_session = AsyncMock()

        with (
            patch(
                "app.api.routes.workflows._get_user_config_by_id",
                new_callable=AsyncMock,
                return_value=config,
            ),
            patch("app.api.routes.workflows.create_agent", return_value=mock_agent),
            patch(
                "app.api.routes.workflows.fetch_model_pricing",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("app.api.routes.workflows.calculate_cost", return_value=0.0),
            patch("app.api.routes.workflows.model_supports_pdf", return_value=False),
            patch(
                "app.api.routes.workflows.evaluate_rubric",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            from app.api.routes.workflows import _run_stage

            result = await _run_stage(
                db=mock_session,
                user_id="user1",
                stage_def={
                    "id": "search",
                    "role": AgentRole.RESEARCHER.value,
                    "task_template": "Search: {input}",
                },
                context="paper content",
                config_id=uuid4(),
            )

        # Old (pre-Task 7) call signature: progress_manager and execution_id
        # are NOT passed.  The agent must not have been called with them.
        assert "progress_manager" not in mock_agent.run.call_args.kwargs
        assert "execution_id" not in mock_agent.run.call_args.kwargs
        assert result["status"] == "completed"
