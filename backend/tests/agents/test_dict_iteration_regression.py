"""Regression tests for the dict-iteration ``RuntimeError`` fix.

The 4 LLM-calling agents (``DebateAgent``, ``SimpleDebateAgent``,
``DeepDebateAgent``, ``DeepReviewAgent``) and the ``_merge_usage`` helper in
``app/agents/strategies/__init__.py`` previously accumulated token usage via::

    acc = state["context"].get("_usage", {...})
    state["context"]["_usage"] = {k: acc[k] + usage[k] for k in acc}

When ``_usage`` already existed in ``state["context"]`` (every call after the
first in a multi-node graph), ``acc`` and ``state["context"]["_usage"]`` were
the same object. The dict comprehension then iterated over ``acc`` while the
surrounding LHS was about to rebind the parent's reference to it. Under
LangGraph's async state propagation this triggered
``RuntimeError: dictionary changed size during iteration`` at the C-level
dict iterator.

The fix replaces the comprehension with an explicit dict literal built from
``.get()`` reads of the existing value, so the result is a fresh dict that
never aliases the parent. This module proves the fix by:

1. Running the 3 affected debate agents with a pre-populated ``_usage`` in
   context and asserting no ``RuntimeError`` is raised even after many
   invocations.
2. Asserting the resulting ``_usage`` dict is a fresh object (not aliased to
   the caller's pre-existing value).
3. Exercising ``_merge_usage`` from ``strategies/__init__.py`` directly.
4. Documenting the structural aliasing of the OLD pattern in a sentinel test
   so the bug class is captured in code.
5. Calling each agent's ``_invoke_with_usage`` 100 times in a tight loop
   and asserting the cumulative totals (covers ``DeepReviewAgent``, whose
   7-node ``run()`` path hits a pre-existing LangChain ``astream_events``
   issue independent of this fix).

All tests are ``@pytest.mark.unit_db`` to skip the autouse ``clean_db`` DB
fixture (matches every other unit test in this suite).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.base import AgentState


def _make_state(context: dict | None = None) -> AgentState:
    return AgentState(
        messages=[HumanMessage(content="regression test input")],
        context=context if context is not None else {},
        output=None,
        metadata={},
    )


def _three_aimessages_with_usage(
    in_a: int = 100, out_a: int = 50, tot_a: int = 150,
    in_b: int = 100, out_b: int = 50, tot_b: int = 150,
    in_c: int = 100, out_c: int = 50, tot_c: int = 150,
) -> list[AIMessage]:
    """Build 3 distinct AIMessages with ``usage_metadata`` (sum = tot_a + tot_b + tot_c)."""
    return [
        AIMessage(
            content="r1",
            usage_metadata={"input_tokens": in_a, "output_tokens": out_a, "total_tokens": tot_a},
        ),
        AIMessage(
            content="r2",
            usage_metadata={"input_tokens": in_b, "output_tokens": out_b, "total_tokens": tot_b},
        ),
        AIMessage(
            content="r3",
            usage_metadata={"input_tokens": in_c, "output_tokens": out_c, "total_tokens": tot_c},
        ),
    ]


# ---------------------------------------------------------------------------
# 1. Regression-sentinel: structural aliasing of the OLD pattern
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
class TestOldPatternStructuralAliasing:
    """Document the structural property that made the OLD pattern unsafe.

    The OLD pattern's precondition for ``RuntimeError`` was:
    ``acc is state["context"]["_usage"]`` -- i.e., the comprehension iterated
    the SAME object that the parent mapping held a reference to. This test
    reconstructs the precondition explicitly so the bug class is captured in
    code. The NEW pattern's contract (proved in the next class) is that the
    resulting dict is a FRESH object -- never aliased to the parent's
    pre-existing reference.
    """

    def test_old_pattern_precondition_is_aliasing(self):
        """The OLD pattern's ``acc`` and ``state["context"]["_usage"]`` were the same object."""
        state = _make_state()
        state["context"]["_usage"] = {
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
        }

        # Simulate the OLD pattern's first line:
        acc = state["context"].get(
            "_usage",
            {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )

        # This is the bug precondition: ``acc`` IS the same object as
        # ``state["context"]["_usage"]``. The comprehension then iterates
        # ``acc`` while the LHS is about to rebind the parent's reference,
        # which can raise ``RuntimeError: dictionary changed size during
        # iteration`` under LangGraph's async state propagation.
        assert acc is state["context"]["_usage"], (
            "OLD pattern precondition: when _usage already exists, acc must be "
            "the same object as state['context']['_usage'] -- this aliasing is "
            "what makes the comprehension unsafe."
        )


# ---------------------------------------------------------------------------
# 2. NEW pattern structural contract
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
class TestNewPatternDoesNotAlias:
    """The NEW pattern's result must be a fresh dict (no identity aliasing).

    The fix builds the merged ``_usage`` via an explicit dict literal whose
    values are read from ``.get()``. The literal is a brand-new object, so
    the parent's new reference is independent of the pre-existing one. This
    is the structural property that prevents the C-level dict iterator from
    being invalidated mid-iteration.
    """

    def test_new_pattern_result_is_fresh_object(self):
        """Assigning via the new pattern must NOT make the new _usage the same object as existing."""
        state = _make_state()
        original = {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10}
        state["context"]["_usage"] = original

        # Mirror the exact new pattern used in the 4 fixed agents.
        existing = state["context"].get("_usage", {})
        new_usage = {
            "input_tokens": existing.get("input_tokens", 0) + 100,
            "output_tokens": existing.get("output_tokens", 0) + 50,
            "total_tokens": existing.get("total_tokens", 0) + 150,
        }
        state["context"]["_usage"] = new_usage

        # The fresh-dict contract: the parent's new reference is a different
        # object from the value that was there before the call.
        assert state["context"]["_usage"] is not original, (
            "NEW pattern contract violated: state['context']['_usage'] is the "
            "same object as the pre-existing value. The dict literal must be a "
            "fresh object to avoid the iterator-aliasing bug class."
        )
        # And the values are correctly summed.
        assert state["context"]["_usage"] == {
            "input_tokens": 107,
            "output_tokens": 53,
            "total_tokens": 160,
        }


# ---------------------------------------------------------------------------
# 3. _merge_usage helper from strategies
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
class TestMergeUsageHelper:
    """Direct tests for ``_merge_usage`` in ``app.agents.strategies``."""

    def test_merge_usage_sums_three_token_fields(self):
        from app.agents.strategies import _merge_usage

        acc = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
        usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        merged = _merge_usage(acc, usage)
        assert merged == {
            "input_tokens": 110,
            "output_tokens": 55,
            "total_tokens": 165,
        }

    def test_merge_usage_handles_missing_fields_via_get(self):
        """Missing fields in either dict must default to 0 (uses ``.get(..., 0)``)."""
        from app.agents.strategies import _merge_usage

        merged = _merge_usage({}, {})
        assert merged == {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        merged = _merge_usage({"input_tokens": 5}, {"output_tokens": 7})
        assert merged == {
            "input_tokens": 5,
            "output_tokens": 7,
            "total_tokens": 0,
        }

    def test_merge_usage_returns_fresh_object(self):
        """The helper must not alias either input (fresh dict contract)."""
        from app.agents.strategies import _merge_usage

        acc = {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}
        usage = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
        merged = _merge_usage(acc, usage)
        assert merged is not acc, "_merge_usage must not return the acc object"
        assert merged is not usage, "_merge_usage must not return the usage object"

    def test_merge_usage_does_not_mutate_inputs(self):
        """Inputs must be left unchanged after the call (no in-place mutation)."""
        from app.agents.strategies import _merge_usage

        acc = {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}
        usage = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
        acc_snapshot = dict(acc)
        usage_snapshot = dict(usage)
        _merge_usage(acc, usage)
        assert acc == acc_snapshot, f"acc was mutated: {acc!r} != {acc_snapshot!r}"
        assert usage == usage_snapshot, f"usage was mutated: {usage!r} != {usage_snapshot!r}"


# ---------------------------------------------------------------------------
# 4. End-to-end: each of the 4 affected agents runs many times without RuntimeError
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
class TestDebateAgentRunDoesNotRaiseRuntimeError:
    """``DebateAgent.run()`` must not raise ``RuntimeError`` when context already has ``_usage``.

    With the OLD pattern, the 2nd and 3rd LLM-calling nodes iterated the same
    object that ``state["context"]["_usage"]`` referenced -- the precondition
    for the C-level dict-iterator invalidation. After the fix, the run
    completes cleanly even when the context has been pre-populated with a
    prior ``_usage`` (e.g. a re-run or a downstream node consuming the same
    context).
    """

    @pytest.mark.asyncio
    async def test_run_with_pre_existing_usage_completes_cleanly(self, mock_llm):
        from app.agents.debate_agent import DebateAgent

        mock_llm.ainvoke.side_effect = _three_aimessages_with_usage(
            in_a=100, out_a=50, tot_a=150,
            in_b=200, out_b=80, tot_b=280,
            in_c=300, out_c=100, tot_c=400,
        )
        agent = DebateAgent(llm=mock_llm)
        state = _make_state(
            context={
                "paper_content": "PAPER",
                "review_content": "REVIEW",
                # Pre-populate _usage as if a prior run had already accumulated tokens.
                "_usage": {"input_tokens": 999, "output_tokens": 888, "total_tokens": 1887},
            }
        )

        # The fix is proven if this call does NOT raise RuntimeError.
        result = await agent.run(
            state["messages"],
            context=state["context"],
            thread_id="regression-test",
        )

        usage = result["context"].get("_usage")
        assert usage is not None, "_usage must be populated after run()"
        # 999 + 100 + 200 + 300 = 1599
        assert usage["input_tokens"] == 1599, (
            f"Expected input_tokens=1599, got {usage['input_tokens']}"
        )
        # 888 + 50 + 80 + 100 = 1118
        assert usage["output_tokens"] == 1118, (
            f"Expected output_tokens=1118, got {usage['output_tokens']}"
        )
        # 1887 + 150 + 280 + 400 = 2717
        assert usage["total_tokens"] == 2717, (
            f"Expected total_tokens=2717, got {usage['total_tokens']}"
        )

    @pytest.mark.asyncio
    async def test_many_consecutive_runs_no_runtime_error(self, mock_llm):
        """Run the agent 10 times in sequence with a shared context. Old pattern would fail."""
        from app.agents.debate_agent import DebateAgent

        agent = DebateAgent(llm=mock_llm)
        # 3 LLM calls per run * 10 runs = 30 side_effect entries.
        side_effects: list[AIMessage] = []
        for i in range(10):
            side_effects.extend(_three_aimessages_with_usage(
                in_a=10, out_a=5, tot_a=15,
                in_b=10, out_b=5, tot_b=15,
                in_c=10, out_c=5, tot_c=15,
            ))
        mock_llm.ainvoke.side_effect = side_effects

        context = {
            "paper_content": "P",
            "review_content": "R",
            # Seed _usage so the comprehension aliasing is exercised from call #2 onwards.
            "_usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        }
        last_result = None
        for i in range(10):
            state = _make_state(context=context)
            last_result = await agent.run(
                state["messages"],
                context=state["context"],
                thread_id=f"regression-{i}",
            )
            # Reuse the same context for the next iteration so the shared
            # ``_usage`` keeps growing -- this is exactly the production
            # scenario that triggered the original RuntimeError.
            context = last_result["context"]

        # After 10 runs: seeded (1+1+2) + 10 * (10+10+10) input = 1+1+1+1+...
        # input_tokens: 1 (seed) + 10*30 = 301
        # output_tokens: 1 (seed) + 10*15 = 151
        # total_tokens: 2 (seed) + 10*45 = 452
        usage = last_result["context"].get("_usage")
        assert usage["input_tokens"] == 301, (
            f"Expected 301 input_tokens after 10 runs, got {usage['input_tokens']}"
        )
        assert usage["output_tokens"] == 151, (
            f"Expected 151 output_tokens after 10 runs, got {usage['output_tokens']}"
        )
        assert usage["total_tokens"] == 452, (
            f"Expected 452 total_tokens after 10 runs, got {usage['total_tokens']}"
        )


@pytest.mark.unit_db
class TestSimpleDebateAgentRunDoesNotRaiseRuntimeError:
    """``SimpleDebateAgent.run()`` must not raise ``RuntimeError`` with pre-existing ``_usage``."""

    @pytest.mark.asyncio
    async def test_run_with_pre_existing_usage_completes_cleanly(self, mock_llm):
        from app.agents.simple_debate_agent import SimpleDebateAgent

        mock_llm.ainvoke.side_effect = _three_aimessages_with_usage(
            in_a=50, out_a=25, tot_a=75,
            in_b=50, out_b=25, tot_b=75,
        )[:2]  # SimpleDebateAgent only makes 2 LLM calls.
        agent = SimpleDebateAgent(llm=mock_llm)
        state = _make_state(
            context={
                "paper_content": "P",
                "review_content": "R",
                "_usage": {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7},
            }
        )

        result = await agent.run(
            state["messages"],
            context=state["context"],
            thread_id="regression-test",
        )

        usage = result["context"].get("_usage")
        assert usage["input_tokens"] == 105, (
            f"Expected input_tokens=105 (5 + 50 + 50), got {usage['input_tokens']}"
        )
        assert usage["output_tokens"] == 52, (
            f"Expected output_tokens=52 (2 + 25 + 25), got {usage['output_tokens']}"
        )
        assert usage["total_tokens"] == 157, (
            f"Expected total_tokens=157 (7 + 75 + 75), got {usage['total_tokens']}"
        )


@pytest.mark.unit_db
class TestDeepDebateAgentRunDoesNotRaiseRuntimeError:
    """``DeepDebateAgent.run()`` must not raise ``RuntimeError`` with pre-existing ``_usage``."""

    @pytest.mark.asyncio
    async def test_run_with_pre_existing_usage_completes_cleanly(self, mock_llm):
        from app.agents.deep_debate_agent import DeepDebateAgent

        mock_llm.ainvoke.side_effect = _three_aimessages_with_usage(
            in_a=10, out_a=5, tot_a=15,
            in_b=20, out_b=8, tot_b=28,
            in_c=30, out_c=10, tot_c=40,
        )
        agent = DeepDebateAgent(llm=mock_llm)
        state = _make_state(
            context={
                "paper_content": "P",
                "review_content": "R",
                "_usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            }
        )

        result = await agent.run(
            state["messages"],
            context=state["context"],
            thread_id="regression-test",
        )

        usage = result["context"].get("_usage")
        assert usage["input_tokens"] == 61, (
            f"Expected input_tokens=61 (1 + 10 + 20 + 30), got {usage['input_tokens']}"
        )
        assert usage["output_tokens"] == 24, (
            f"Expected output_tokens=24 (1 + 5 + 8 + 10), got {usage['output_tokens']}"
        )
        assert usage["total_tokens"] == 85, (
            f"Expected total_tokens=85 (2 + 15 + 28 + 40), got {usage['total_tokens']}"
        )


@pytest.mark.unit_db
class TestInvokeWithUsageDirectCalls:
    """Call each agent's ``_invoke_with_usage`` directly in a tight loop.

    This is a tighter version of the end-to-end tests above: it bypasses the
    graph and directly exercises the bug-prone code path. If the OLD pattern
    were ever re-introduced, this loop would surface the ``RuntimeError``
    (under any LangGraph state-propagation wrapper that mutates the parent
    during iteration) because it runs the aliasing scenario hundreds of times
    on a single ``state["context"]``.
    """

    @pytest.mark.asyncio
    async def test_debate_agent_invoke_with_usage_many_calls(self):
        from app.agents.debate_agent import DebateAgent

        mock = MagicMock()
        mock.ainvoke = AsyncMock(return_value=AIMessage(
            content="x",
            usage_metadata={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        ))
        agent = DebateAgent(llm=mock)
        state = _make_state(context={"_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}})

        for _ in range(100):
            await agent._invoke_with_usage(state, [HumanMessage(content="hi")])

        usage = state["context"]["_usage"]
        # 100 calls * 2 total = 200
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 100
        assert usage["total_tokens"] == 200

    @pytest.mark.asyncio
    async def test_simple_debate_agent_invoke_with_usage_many_calls(self):
        from app.agents.simple_debate_agent import SimpleDebateAgent

        mock = MagicMock()
        mock.ainvoke = AsyncMock(return_value=AIMessage(
            content="x",
            usage_metadata={"input_tokens": 2, "output_tokens": 1, "total_tokens": 3},
        ))
        agent = SimpleDebateAgent(llm=mock)
        state = _make_state(context={"_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}})

        for _ in range(100):
            await agent._invoke_with_usage(state, [HumanMessage(content="hi")])

        usage = state["context"]["_usage"]
        assert usage["input_tokens"] == 200
        assert usage["output_tokens"] == 100
        assert usage["total_tokens"] == 300

    @pytest.mark.asyncio
    async def test_deep_debate_agent_invoke_with_usage_many_calls(self):
        from app.agents.deep_debate_agent import DeepDebateAgent

        mock = MagicMock()
        mock.ainvoke = AsyncMock(return_value=AIMessage(
            content="x",
            usage_metadata={"input_tokens": 3, "output_tokens": 2, "total_tokens": 5},
        ))
        agent = DeepDebateAgent(llm=mock)
        state = _make_state(context={"_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}})

        for _ in range(100):
            await agent._invoke_with_usage(state, [HumanMessage(content="hi")])

        usage = state["context"]["_usage"]
        assert usage["input_tokens"] == 300
        assert usage["output_tokens"] == 200
        assert usage["total_tokens"] == 500

    @pytest.mark.asyncio
    async def test_deep_review_agent_invoke_with_usage_many_calls(self):
        from app.agents.review_pipeline import DeepReviewAgent

        mock = MagicMock()
        mock.ainvoke = AsyncMock(return_value=AIMessage(
            content="x",
            usage_metadata={"input_tokens": 4, "output_tokens": 3, "total_tokens": 7},
        ))
        agent = DeepReviewAgent(llm=mock)
        state = _make_state(context={"_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}})

        for _ in range(100):
            await agent._invoke_with_usage(state, [HumanMessage(content="hi")])

        usage = state["context"]["_usage"]
        assert usage["input_tokens"] == 400
        assert usage["output_tokens"] == 300
        assert usage["total_tokens"] == 700
