"""Unit tests for agent execution strategies (Task 3).

Verifies that each :class:`AgentStrategy` emits the expected
``STRATEGY_ITERATION`` events and that every strategy ends with a
``STRATEGY_COMPLETE`` event whose ``result`` is the final ``AIMessage``.

Pattern: ``mock_llm.ainvoke.side_effect = [AIMessage(...), ...]`` is used to
feed a deterministic sequence of LLM responses. The strategies are called via
``async for event in strategy.execute(...)`` and the event stream is asserted
event-by-event.

Event counts (per spec, the "exactly N events" assertions count
``STRATEGY_ITERATION`` events only; a single ``STRATEGY_COMPLETE`` terminates
each stream):
- DirectStrategy: 1 ITERATION + 1 COMPLETE  (2 total)
- CritiqueStrategy(max_iterations=N): 3*N ITERATION + 1 COMPLETE
- ReflectionStrategy(max_iterations=N): 2*N ITERATION + 1 COMPLETE
- EvaluatorOptimizerStrategy: variable (threshold-dependent) + 1 COMPLETE
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from app.agents.strategies import (
    CritiqueStrategy,
    DirectStrategy,
    EvaluatorOptimizerStrategy,
    EventType,
    ReflectionStrategy,
    StrategyEvent,
    get_strategy,
)


def _llm_returning(*contents: str) -> MagicMock:
    """Return a MagicMock whose ``ainvoke`` yields the given AIMessages in order."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(side_effect=[AIMessage(content=c) for c in contents])
    return mock


@pytest.mark.unit_db
class TestEventTypeAndModel:
    """The EventType enum and StrategyEvent model are public API."""

    def test_event_type_string_values(self):
        assert EventType.STRATEGY_ITERATION.value == "strategy.iteration"
        assert EventType.STRATEGY_COMPLETE.value == "strategy.complete"

    def test_strategy_event_required_fields(self):
        event = StrategyEvent(
            type=EventType.STRATEGY_ITERATION,
            phase="generate",
            iteration=1,
            max_iterations=1,
        )
        assert event.type is EventType.STRATEGY_ITERATION
        assert event.phase == "generate"
        assert event.iteration == 1
        assert event.max_iterations == 1
        assert event.score is None
        assert event.result is None

    def test_strategy_event_carries_result_on_complete(self):
        msg = AIMessage(content="hello")
        event = StrategyEvent(
            type=EventType.STRATEGY_COMPLETE,
            phase="complete",
            iteration=1,
            max_iterations=1,
            result=msg,
        )
        assert event.result is msg
        assert event.result.content == "hello"


@pytest.mark.unit_db
@pytest.mark.asyncio
class TestDirectStrategy:
    """DirectStrategy: single LLM call, exactly one STRATEGY_ITERATION event."""

    async def test_emits_exactly_one_iteration_event(self):
        mock_llm = _llm_returning("Direct response")
        strategy = get_strategy("direct")
        assert isinstance(strategy, DirectStrategy)

        events: list[StrategyEvent] = []
        async for event in strategy.execute(mock_llm, [], "system prompt"):
            events.append(event)

        # 1 ITERATION + 1 COMPLETE
        assert len(events) == 2, (
            f"Expected 2 events (1 ITERATION + 1 COMPLETE), got {len(events)}: "
            f"{[e.type for e in events]}"
        )
        assert events[0].type is EventType.STRATEGY_ITERATION
        assert events[0].phase == "generate"
        assert events[0].iteration == 1
        assert events[0].max_iterations == 1

    async def test_complete_event_carries_aimessage(self):
        mock_llm = _llm_returning("Direct response")
        events = [e async for e in DirectStrategy().execute(mock_llm, [], "system prompt")]

        last = events[-1]
        assert last.type is EventType.STRATEGY_COMPLETE
        assert isinstance(last.result, AIMessage), (
            f"STRATEGY_COMPLETE.result must be an AIMessage, got {type(last.result)}"
        )
        assert last.result.content == "Direct response"

    async def test_calls_llm_exactly_once(self):
        mock_llm = _llm_returning("x")
        async for _ in DirectStrategy().execute(mock_llm, [], "sys"):
            pass

        assert mock_llm.ainvoke.call_count == 1, (
            f"DirectStrategy must call LLM exactly once, got {mock_llm.ainvoke.call_count}"
        )


@pytest.mark.unit_db
@pytest.mark.asyncio
class TestCritiqueStrategy:
    """CritiqueStrategy: generate -> critique -> refine per iteration (3 events)."""

    async def test_max_iterations_2_emits_six_iteration_events(self):
        # 2 iterations * 3 LLM calls = 6 AIMessages
        mock_llm = _llm_returning(*[f"resp{i}" for i in range(6)])

        strategy = CritiqueStrategy(max_iterations=2)
        events: list[StrategyEvent] = []
        async for event in strategy.execute(mock_llm, [], "system prompt"):
            events.append(event)

        iteration_events = [e for e in events if e.type is EventType.STRATEGY_ITERATION]
        complete_events = [e for e in events if e.type is EventType.STRATEGY_COMPLETE]

        # The spec's "exactly 6 events" refers to the 6 STRATEGY_ITERATION
        # events; one STRATEGY_COMPLETE terminates the stream.
        assert len(iteration_events) == 6, (
            f"Expected 6 STRATEGY_ITERATION events for max_iterations=2, got "
            f"{len(iteration_events)}"
        )
        assert len(complete_events) == 1, (
            f"Expected exactly 1 STRATEGY_COMPLETE event, got {len(complete_events)}"
        )
        assert len(events) == 7, (
            f"Total events = 6 ITERATION + 1 COMPLETE = 7, got {len(events)}"
        )

    async def test_phase_ordering(self):
        mock_llm = _llm_returning(*[f"resp{i}" for i in range(6)])
        strategy = CritiqueStrategy(max_iterations=2)
        events = [e async for e in strategy.execute(mock_llm, [], "system prompt")]

        iteration_phases = [e.phase for e in events if e.type is EventType.STRATEGY_ITERATION]
        assert iteration_phases == [
            "generate", "critique", "refine",
            "generate", "critique", "refine",
        ], f"Unexpected phase order: {iteration_phases}"

    async def test_iteration_counter_increments(self):
        mock_llm = _llm_returning(*[f"resp{i}" for i in range(6)])
        strategy = CritiqueStrategy(max_iterations=2)
        events = [e async for e in strategy.execute(mock_llm, [], "system prompt")]

        iteration_events = [e for e in events if e.type is EventType.STRATEGY_ITERATION]
        iterations = [e.iteration for e in iteration_events]
        max_iters = [e.max_iterations for e in iteration_events]
        assert iterations == [1, 1, 1, 2, 2, 2], f"Unexpected iteration counter: {iterations}"
        assert all(m == 2 for m in max_iters), (
            f"max_iterations must be 2 on every event, got {max_iters}"
        )

    async def test_complete_event_carries_aimessage(self):
        mock_llm = _llm_returning(*[f"resp{i}" for i in range(6)])
        strategy = CritiqueStrategy(max_iterations=2)
        events = [e async for e in strategy.execute(mock_llm, [], "system prompt")]

        last = events[-1]
        assert last.type is EventType.STRATEGY_COMPLETE
        assert isinstance(last.result, AIMessage)
        # The 6th LLM call is the second "refine" -> resp5
        assert last.result.content == "resp5"

    async def test_calls_llm_three_times_per_iteration(self):
        mock_llm = _llm_returning(*[f"r{i}" for i in range(6)])
        async for _ in CritiqueStrategy(max_iterations=2).execute(mock_llm, [], "sys"):
            pass

        assert mock_llm.ainvoke.call_count == 6, (
            f"CritiqueStrategy(2) must call LLM 6 times, got {mock_llm.ainvoke.call_count}"
        )


@pytest.mark.unit_db
@pytest.mark.asyncio
class TestReflectionStrategy:
    """ReflectionStrategy: generate -> reflect per iteration (2 events)."""

    async def test_max_iterations_3_emits_six_iteration_events(self):
        # 3 iterations * 2 LLM calls = 6 AIMessages
        mock_llm = _llm_returning(*[f"resp{i}" for i in range(6)])

        strategy = ReflectionStrategy(max_iterations=3)
        events: list[StrategyEvent] = []
        async for event in strategy.execute(mock_llm, [], "system prompt"):
            events.append(event)

        iteration_events = [e for e in events if e.type is EventType.STRATEGY_ITERATION]
        complete_events = [e for e in events if e.type is EventType.STRATEGY_COMPLETE]

        assert len(iteration_events) == 6, (
            f"Expected 6 STRATEGY_ITERATION events for max_iterations=3, got "
            f"{len(iteration_events)}"
        )
        assert len(complete_events) == 1, (
            f"Expected exactly 1 STRATEGY_COMPLETE event, got {len(complete_events)}"
        )
        assert len(events) == 7, (
            f"Total events = 6 ITERATION + 1 COMPLETE = 7, got {len(events)}"
        )

    async def test_phase_ordering(self):
        mock_llm = _llm_returning(*[f"resp{i}" for i in range(6)])
        strategy = ReflectionStrategy(max_iterations=3)
        events = [e async for e in strategy.execute(mock_llm, [], "system prompt")]

        iteration_phases = [e.phase for e in events if e.type is EventType.STRATEGY_ITERATION]
        assert iteration_phases == [
            "generate", "reflect",
            "generate", "reflect",
            "generate", "reflect",
        ], f"Unexpected phase order: {iteration_phases}"

    async def test_complete_event_carries_aimessage(self):
        mock_llm = _llm_returning(*[f"resp{i}" for i in range(6)])
        strategy = ReflectionStrategy(max_iterations=3)
        events = [e async for e in strategy.execute(mock_llm, [], "system prompt")]

        last = events[-1]
        assert last.type is EventType.STRATEGY_COMPLETE
        assert isinstance(last.result, AIMessage)
        # The 6th LLM call is the third "reflect" -> resp5
        assert last.result.content == "resp5"

    async def test_calls_llm_two_times_per_iteration(self):
        mock_llm = _llm_returning(*[f"r{i}" for i in range(6)])
        async for _ in ReflectionStrategy(max_iterations=3).execute(mock_llm, [], "sys"):
            pass

        assert mock_llm.ainvoke.call_count == 6, (
            f"ReflectionStrategy(3) must call LLM 6 times, got {mock_llm.ainvoke.call_count}"
        )


@pytest.mark.unit_db
@pytest.mark.asyncio
class TestEvaluatorOptimizerStrategy:
    """EvaluatorOptimizerStrategy: score on evaluate/optimize, threshold break."""

    async def test_evaluate_events_carry_score(self):
        # Below-threshold scores (0.5, 0.6) -> optimize runs both iterations.
        # 1 generate + 2*(evaluate + optimize) = 5 LLM calls
        mock_llm = _llm_returning(
            "initial response",  # generate
            "0.5",                # evaluate iter 1
            "optimized 1",        # optimize iter 1
            "0.6",                # evaluate iter 2
            "optimized 2",        # optimize iter 2
        )

        strategy = EvaluatorOptimizerStrategy(max_iterations=2, quality_threshold=0.8)
        events = [e async for e in strategy.execute(mock_llm, [], "system prompt")]

        scored_events = [
            e for e in events
            if e.type is EventType.STRATEGY_ITERATION and e.phase in ("evaluate", "optimize")
        ]
        assert len(scored_events) >= 2, (
            f"Expected at least 2 evaluate/optimize events, got {len(scored_events)}"
        )
        for event in scored_events:
            assert event.score is not None, (
                f"evaluate/optimize event must carry a score, got None: phase={event.phase}"
            )
            assert isinstance(event.score, float), (
                f"score must be a float, got {type(event.score).__name__}"
            )

    async def test_emits_generate_evaluate_optimize_per_iteration(self):
        mock_llm = _llm_returning(
            "initial",  # generate
            "0.5",      # evaluate iter 1
            "opt1",     # optimize iter 1
            "0.6",      # evaluate iter 2
            "opt2",     # optimize iter 2
        )

        strategy = EvaluatorOptimizerStrategy(max_iterations=2, quality_threshold=0.8)
        events = [e async for e in strategy.execute(mock_llm, [], "system prompt")]

        iteration_phases = [e.phase for e in events if e.type is EventType.STRATEGY_ITERATION]
        # 1 generate + 2*(evaluate + optimize) = 5 ITERATION events
        assert iteration_phases == [
            "generate", "evaluate", "optimize", "evaluate", "optimize",
        ], f"Unexpected phase order: {iteration_phases}"

    async def test_threshold_met_stops_optimization(self):
        # First evaluate returns 0.9 (above 0.8 threshold) -> no optimize call.
        # 1 generate + 1 evaluate = 2 LLM calls
        mock_llm = _llm_returning("initial", "0.9")

        strategy = EvaluatorOptimizerStrategy(max_iterations=3, quality_threshold=0.8)
        events = [e async for e in strategy.execute(mock_llm, [], "system prompt")]

        iteration_phases = [e.phase for e in events if e.type is EventType.STRATEGY_ITERATION]
        assert iteration_phases == ["generate", "evaluate"], (
            f"Threshold met should skip optimize; got: {iteration_phases}"
        )
        eval_event = next(
            e for e in events
            if e.type is EventType.STRATEGY_ITERATION and e.phase == "evaluate"
        )
        assert eval_event.score == 0.9, f"Expected score 0.9, got {eval_event.score}"

    async def test_complete_event_carries_aimessage(self):
        mock_llm = _llm_returning("initial", "0.5", "opt1", "0.6", "opt2")
        strategy = EvaluatorOptimizerStrategy(max_iterations=2, quality_threshold=0.8)
        events = [e async for e in strategy.execute(mock_llm, [], "system prompt")]

        last = events[-1]
        assert last.type is EventType.STRATEGY_COMPLETE
        assert isinstance(last.result, AIMessage)
        # Final response is the second optimize -> "opt2"
        assert last.result.content == "opt2"

    async def test_score_default_when_unparseable(self):
        # Gibberish score -> defaults to 0.0, optimizer runs. Second iter hits threshold.
        mock_llm = _llm_returning(
            "initial",
            "not a number",
            "opt1",
            "0.95",
        )

        strategy = EvaluatorOptimizerStrategy(max_iterations=3, quality_threshold=0.8)
        events = [e async for e in strategy.execute(mock_llm, [], "system prompt")]

        eval_events = [
            e for e in events
            if e.type is EventType.STRATEGY_ITERATION and e.phase == "evaluate"
        ]
        assert len(eval_events) == 2
        assert eval_events[0].score == 0.0, (
            f"Unparseable score must default to 0.0, got {eval_events[0].score}"
        )
        assert eval_events[1].score == 0.95, (
            f"Parsed score 0.95 expected, got {eval_events[1].score}"
        )


@pytest.mark.unit_db
@pytest.mark.asyncio
class TestAllStrategiesReturnAIMessage:
    """Every strategy must end with a STRATEGY_COMPLETE event carrying an AIMessage."""

    async def test_direct_returns_aimessage(self):
        events = [e async for e in DirectStrategy().execute(_llm_returning("d"), [], "sys")]
        assert isinstance(events[-1].result, AIMessage)

    async def test_critique_returns_aimessage(self):
        events = [
            e async for e in
            CritiqueStrategy(max_iterations=1).execute(_llm_returning("c0", "c1", "c2"), [], "sys")
        ]
        assert isinstance(events[-1].result, AIMessage)

    async def test_reflection_returns_aimessage(self):
        events = [
            e async for e in
            ReflectionStrategy(max_iterations=1).execute(_llm_returning("r0", "r1"), [], "sys")
        ]
        assert isinstance(events[-1].result, AIMessage)

    async def test_evaluator_optimizer_returns_aimessage(self):
        # 0.9 >= 0.8 -> threshold met, no optimize
        events = [
            e async for e in
            EvaluatorOptimizerStrategy(max_iterations=2, quality_threshold=0.8)
            .execute(_llm_returning("init", "0.9"), [], "sys")
        ]
        assert isinstance(events[-1].result, AIMessage)


@pytest.mark.unit_db
class TestGetStrategyFactory:
    """The ``get_strategy`` factory returns the right concrete class."""

    def test_direct_factory(self):
        s = get_strategy("direct")
        assert isinstance(s, DirectStrategy)
        assert s.max_iterations == 1

    def test_critique_factory_with_max_iterations(self):
        s = get_strategy("critique", max_iterations=5)
        assert isinstance(s, CritiqueStrategy)
        assert s.max_iterations == 5

    def test_reflection_factory_with_max_iterations(self):
        s = get_strategy("reflection", max_iterations=4)
        assert isinstance(s, ReflectionStrategy)
        assert s.max_iterations == 4

    def test_evaluator_optimizer_factory(self):
        s = get_strategy("evaluator_optimizer", max_iterations=3, quality_threshold=0.9)
        assert isinstance(s, EvaluatorOptimizerStrategy)
        assert s.max_iterations == 3
        assert s.quality_threshold == 0.9

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("nonexistent")
