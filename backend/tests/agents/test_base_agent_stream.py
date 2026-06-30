"""Unit tests for BaseAgent.run() with astream_events + ProgressManager.

Verifies Task 6 acceptance criteria:
- run() with progress_manager emits NODE_STARTED + NODE_COMPLETED per graph node
- Strategy events correctly interspersed with node events
- Return value matches the pre-Task-6 structure
- Cancellation interrupts streaming
- Backward compat: existing agents (DebateAgent) still work without progress_manager
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph

from app.agents.base import AgentState, BaseAgent
from app.agents.strategies import (
    EventType as StrategyEventType,
    StrategyEvent,
)
from app.services.progress import (
    EventType as ProgressEventType,
    ExecutionEvent,
    ProgressManager,
)


@pytest.fixture
def progress_manager(monkeypatch):
    """Return a ProgressManager whose ``publish`` captures events for assertions.

    The real ``publish`` fans out to local subscribers, Redis, and the DB.
    For unit_db tests we replace it with a recorder that appends every
    event to a ``published`` list. The Redis/DB background tasks are also
    no-op'd to keep the test self-contained.
    """
    pm = ProgressManager(redis_client=None)
    pm.published = []  # type: ignore[attr-defined]

    original_publish = pm.publish

    async def recording_publish(execution_id, event):
        pm.published.append(event)  # type: ignore[attr-defined]

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(pm, "publish", recording_publish)
    monkeypatch.setattr(pm, "_publish_to_redis", _noop)
    monkeypatch.setattr(pm, "_persist_to_db", _noop)
    pm.reset()
    return pm


class _GraphAgent(BaseAgent):
    """Minimal BaseAgent whose ``graph.astream_events`` yields a fixture list.

    Tests construct the agent with a list of LangGraph events. The mocked
    ``graph.astream_events`` yields them in order so we can assert exactly
    which events are published without running a real graph.
    """

    name = "test"
    description = "test agent"
    system_prompt = "You are a test agent."

    def __init__(self, llm, events=None, final_state=None):
        super().__init__(llm=llm, strategy_name="direct")
        self._events = list(events or [])
        self._final_state_override = final_state

    def build_graph(self) -> StateGraph:
        raise NotImplementedError("not used — graph is mocked")

    @property
    def graph(self):
        graph = MagicMock()

        async def fake_astream_events(state, config, version):
            for ev in self._events:
                yield ev

        graph.astream_events = fake_astream_events
        return graph


def _root_chain_events(state: dict[str, Any], inner: list[dict[str, Any]]):
    """Wrap inner events with the LangGraph root chain (``on_chain_start``/
    ``on_chain_end`` named ``"LangGraph"``) so the run() filter excludes them.
    """
    output = {"output": state}
    return [
        {"event": "on_chain_start", "name": "LangGraph", "data": {"input": state}},
        *inner,
        {"event": "on_chain_end", "name": "LangGraph", "data": output},
    ]


def _node_event_pair(name: str, state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return (on_chain_start, on_chain_end) for a single node."""
    return [
        {"event": "on_chain_start", "name": name, "data": {"input": state}},
        {"event": "on_chain_end", "name": name, "data": {"output": state}},
    ]


@pytest.mark.unit_db
class TestRunPublishesNodeEvents:
    """run() must publish NODE_STARTED and NODE_COMPLETED for each graph node."""

    @pytest.mark.asyncio
    async def test_node_started_and_completed_emitted_for_each_node(
        self, mock_llm, progress_manager
    ):
        state = {
            "messages": [HumanMessage(content="hi")],
            "context": {},
            "output": "graph produced this",
            "metadata": {},
        }
        events = _root_chain_events(
            state,
            [
                *_node_event_pair("alpha", state),
                *_node_event_pair("beta", state),
            ],
        )
        agent = _GraphAgent(llm=mock_llm, events=events, final_state=state)
        exec_id = uuid4()

        result = await agent.run(
            messages=[HumanMessage(content="hi")],
            execution_id=exec_id,
            progress_manager=progress_manager,
        )

        started = [
            e
            for e in progress_manager.published
            if e.event_type is ProgressEventType.NODE_STARTED
        ]
        completed = [
            e
            for e in progress_manager.published
            if e.event_type is ProgressEventType.NODE_COMPLETED
        ]
        assert [e.data["node_name"] for e in started] == ["alpha", "beta"]
        assert [e.data["node_name"] for e in completed] == ["alpha", "beta"]
        # NODE_STARTED carries the agent type for downstream filtering.
        for ev in started:
            assert ev.data["agent_type"] == "test"
        # NODE_COMPLETED carries a duration_ms (>= 0).
        for ev in completed:
            assert ev.data["status"] == "completed"
            assert isinstance(ev.data["duration_ms"], int)
            assert ev.data["duration_ms"] >= 0
        assert result["output"] == "graph produced this"

    @pytest.mark.asyncio
    async def test_tool_call_and_complete_events_emitted(
        self, mock_llm, progress_manager
    ):
        state = {
            "messages": [HumanMessage(content="hi")],
            "context": {},
            "output": "graph done",
            "metadata": {},
        }
        inner = [
            *_node_event_pair("alpha", state),
            {
                "event": "on_tool_start",
                "name": "search_papers",
                "data": {"input": {"query": "deep learning " * 50}},
            },
            {
                "event": "on_tool_end",
                "name": "search_papers",
                "data": {"output": "ok"},
            },
        ]
        events = _root_chain_events(state, inner)
        agent = _GraphAgent(llm=mock_llm, events=events, final_state=state)
        exec_id = uuid4()

        await agent.run(
            messages=[HumanMessage(content="hi")],
            execution_id=exec_id,
            progress_manager=progress_manager,
        )

        tool_calls = [
            e
            for e in progress_manager.published
            if e.event_type is ProgressEventType.TOOL_CALL
        ]
        tool_done = [
            e
            for e in progress_manager.published
            if e.event_type is ProgressEventType.TOOL_COMPLETE
        ]
        assert len(tool_calls) == 1
        assert tool_calls[0].data["tool_name"] == "search_papers"
        # input_truncated is capped to keep the SSE payload small.
        assert len(tool_calls[0].data["input_truncated"]) <= 203
        assert tool_calls[0].data["input_truncated"].endswith("...")
        assert len(tool_done) == 1
        assert tool_done[0].data["tool_name"] == "search_papers"
        assert tool_done[0].data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_no_events_published_without_progress_manager(self, mock_llm):
        """Backward compat: agents.run(...) with no progress_manager publishes nothing."""
        state = {
            "messages": [HumanMessage(content="hi")],
            "context": {},
            "output": "graph done",
            "metadata": {},
        }
        events = _root_chain_events(state, _node_event_pair("alpha", state))
        agent = _GraphAgent(llm=mock_llm, events=events, final_state=state)

        result = await agent.run(
            messages=[HumanMessage(content="hi")],
            thread_id="t1",
        )

        assert result["output"] == "graph done"


# ---------------------------------------------------------------------------
# Strategy events
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
class TestRunInvokesStrategy:
    """When the graph does NOT produce output, the strategy is invoked."""

    @pytest.mark.asyncio
    async def test_strategy_runs_when_graph_output_empty(
        self, mock_llm, progress_manager, monkeypatch
    ):
        # Graph does NOT set state["output"].
        empty_state = {
            "messages": [HumanMessage(content="hi")],
            "context": {},
            "output": None,
            "metadata": {},
        }
        events = _root_chain_events(empty_state, _node_event_pair("alpha", empty_state))
        agent = _GraphAgent(llm=mock_llm, events=events, final_state=empty_state)

        # DirectStrategy emits one STRATEGY_ITERATION ("generate") + one
        # STRATEGY_COMPLETE carrying the AIMessage.
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(
                content="strategy output",
                usage_metadata={
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "total_tokens": 30,
                },
            )
        )
        exec_id = uuid4()

        result = await agent.run(
            messages=[HumanMessage(content="hi")],
            execution_id=exec_id,
            progress_manager=progress_manager,
        )

        strategy_events = [
            e
            for e in progress_manager.published
            if e.event_type is ProgressEventType.STRATEGY_ITERATION
        ]
        assert len(strategy_events) == 1
        assert strategy_events[0].data["phase"] == "generate"
        assert strategy_events[0].data["iteration"] == 1
        assert strategy_events[0].data["max_iterations"] == 1
        # The strategy's final response becomes state["output"].
        assert result["output"] == "strategy output"
        # The AIMessage is appended to messages.
        assert any(
            isinstance(m, AIMessage) and m.content == "strategy output"
            for m in result["messages"]
        )
        # mock_llm was invoked exactly once (the strategy's LLM call).
        assert mock_llm.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_strategy_skipped_when_graph_produced_output(
        self, mock_llm, progress_manager
    ):
        """Backward compat: DebateAgent's graph already produces output, so
        the strategy is a no-op and the strategy does NOT make an LLM call."""
        state = {
            "messages": [HumanMessage(content="hi")],
            "context": {},
            "output": "graph produced this final text",
            "metadata": {},
        }
        events = _root_chain_events(state, _node_event_pair("alpha", state))
        agent = _GraphAgent(llm=mock_llm, events=events, final_state=state)
        exec_id = uuid4()

        result = await agent.run(
            messages=[HumanMessage(content="hi")],
            execution_id=exec_id,
            progress_manager=progress_manager,
        )

        # The strategy was NOT invoked (no LLM call beyond the graph's).
        assert mock_llm.ainvoke.call_count == 0
        # The graph's output survives untouched.
        assert result["output"] == "graph produced this final text"
        # No STRATEGY_ITERATION events were published.
        strategy_events = [
            e
            for e in progress_manager.published
            if e.event_type is ProgressEventType.STRATEGY_ITERATION
        ]
        assert strategy_events == []


# ---------------------------------------------------------------------------
# Return value structure
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
class TestRunReturnValue:
    """Return value must match the pre-Task-6 dict structure."""

    @pytest.mark.asyncio
    async def test_return_dict_has_expected_keys(self, mock_llm, progress_manager):
        state = {
            "messages": [HumanMessage(content="hi")],
            "context": {"foo": "bar", "_usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}},
            "output": "result text",
            "metadata": {"agent": "test"},
        }
        events = _root_chain_events(state, _node_event_pair("alpha", state))
        agent = _GraphAgent(llm=mock_llm, events=events, final_state=state)
        exec_id = uuid4()

        result = await agent.run(
            messages=[HumanMessage(content="hi")],
            context={"foo": "bar"},
            thread_id="t1",
            execution_id=exec_id,
            progress_manager=progress_manager,
        )

        assert isinstance(result, dict)
        assert set(result.keys()) >= {"messages", "context", "output", "metadata"}
        assert result["output"] == "result text"
        assert result["context"].get("foo") == "bar"
        assert result["metadata"]["usage"] == {
            "input_tokens": 1,
            "output_tokens": 2,
            "total_tokens": 3,
        }

    @pytest.mark.asyncio
    async def test_return_value_structure_without_progress_manager(self, mock_llm):
        """Same return value when progress_manager is not provided."""
        state = {
            "messages": [HumanMessage(content="hi")],
            "context": {},
            "output": "graph result",
            "metadata": {"agent": "test"},
        }
        events = _root_chain_events(state, _node_event_pair("alpha", state))
        agent = _GraphAgent(llm=mock_llm, events=events, final_state=state)

        result = await agent.run(
            messages=[HumanMessage(content="hi")],
            thread_id="t1",
        )

        assert set(result.keys()) >= {"messages", "context", "output", "metadata"}
        assert result["output"] == "graph result"


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
class TestRunCancellation:
    """Cancellation flag set via Redis must interrupt streaming."""

    @pytest.mark.asyncio
    async def test_cancellation_breaks_streaming_loop(
        self, mock_llm, progress_manager
    ):
        from app.tasks.cancel import set_cancel, clear_cancel

        state = {
            "messages": [HumanMessage(content="hi")],
            "context": {},
            "output": "graph output",
            "metadata": {},
        }
        events = _root_chain_events(
            state,
            [
                *_node_event_pair("alpha", state),
                *_node_event_pair("beta", state),
                *_node_event_pair("gamma", state),
            ],
        )
        agent = _GraphAgent(llm=mock_llm, events=events, final_state=state)
        exec_id = uuid4()
        await set_cancel(str(exec_id))
        try:
            result = await agent.run(
                messages=[HumanMessage(content="hi")],
                execution_id=exec_id,
                progress_manager=progress_manager,
            )
            node_started = [
                e
                for e in progress_manager.published
                if e.event_type is ProgressEventType.NODE_STARTED
            ]
            assert node_started == []
            assert "messages" in result
        finally:
            await clear_cancel(str(exec_id))

    @pytest.mark.asyncio
    async def test_cancel_flag_for_other_execution_does_not_affect_us(
        self, mock_llm, progress_manager
    ):
        """The agent only consults the cancel flag for its own execution_id."""
        from app.tasks.cancel import set_cancel, clear_cancel

        other_id = uuid4()
        await set_cancel(str(other_id))
        state = {
            "messages": [HumanMessage(content="hi")],
            "context": {},
            "output": "graph done",
            "metadata": {},
        }
        events = _root_chain_events(state, _node_event_pair("alpha", state))
        agent = _GraphAgent(llm=mock_llm, events=events, final_state=state)
        my_id = uuid4()
        try:
            result = await agent.run(
                messages=[HumanMessage(content="hi")],
                execution_id=my_id,
                progress_manager=progress_manager,
            )
            started = [
                e
                for e in progress_manager.published
                if e.event_type is ProgressEventType.NODE_STARTED
            ]
            assert len(started) == 1
            assert result["output"] == "graph done"
        finally:
            await clear_cancel(str(other_id))
