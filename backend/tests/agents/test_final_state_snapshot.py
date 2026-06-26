"""Regression tests for the final_state snapshot fix in BaseAgent.run().

Bug: the previous implementation called ``copy.deepcopy(output)`` inside
the ``astream_events`` for-loop, once per ``on_chain_end`` event. Under
LangGraph async state propagation, this triggered
``RuntimeError: dictionary changed size during iteration`` while the
C-level dict iteration was in progress.

Fix: track only the last dict output as a reference, then take a single
deep copy AFTER the stream has drained, with a shallow-copy fallback
if the deep copy still raises.

These tests exercise the snapshot path directly via a mocked graph so
the regression is caught even without a real LLM.
"""
from __future__ import annotations

import copy
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph

from app.agents.base import BaseAgent


class _GraphAgent(BaseAgent):
    name = "snapshot-test"
    description = "tests final_state snapshot semantics"
    system_prompt = "test"

    def __init__(self, llm, events):
        super().__init__(llm=llm, strategy_name="direct")
        self._events = list(events)

    def build_graph(self) -> StateGraph:
        raise NotImplementedError("graph is mocked")

    @property
    def graph(self):
        graph_obj = type("G", (), {})()

        async def fake_astream_events(state, config, version):
            for ev in self._events:
                yield ev

        graph_obj.astream_events = fake_astream_events
        return graph_obj


def _node_pair(name: str, output: dict[str, Any]):
    return [
        {"event": "on_chain_start", "name": name, "data": {"input": {}}},
        {"event": "on_chain_end", "name": name, "data": {"output": output}},
    ]


def _final_chain_end(state: dict[str, Any]):
    return {"event": "on_chain_end", "name": "LangGraph", "data": {"output": state}}


@pytest.mark.unit_db
class TestFinalStateSnapshotSemantics:
    """The final state must be an independent snapshot of the graph's output."""

    @pytest.mark.asyncio
    async def test_deepcopy_called_once_not_per_event(self, mock_llm):
        graph_state: dict[str, Any] = {
            "messages": [HumanMessage(content="hi")],
            "context": {"paper_content": "p", "review_content": "r"},
            "output": "graph result",
            "metadata": {},
        }
        events = [
            {"event": "on_chain_start", "name": "LangGraph", "data": {"input": {}}},
            *_node_pair("alpha", graph_state),
            *_node_pair("beta", graph_state),
            *_node_pair("gamma", graph_state),
            _final_chain_end(graph_state),
        ]
        agent = _GraphAgent(llm=mock_llm, events=events)
        with patch("app.agents.base.copy.deepcopy", wraps=copy.deepcopy) as spy:
            await agent.run(
                messages=[HumanMessage(content="hi")],
                context={"paper_content": "p", "review_content": "r"},
                execution_id=uuid4(),
                progress_manager=None,
            )
        assert spy.call_count == 1, (
            f"deepcopy must run exactly once after the stream drains; "
            f"got {spy.call_count} calls (one per on_chain_end is the old bug)"
        )

    @pytest.mark.asyncio
    async def test_returned_state_is_independent_snapshot(self, mock_llm):
        graph_state: dict[str, Any] = {
            "messages": [HumanMessage(content="hi")],
            "context": {"paper_content": "p", "review_content": "r"},
            "output": "graph result",
            "metadata": {"k": "v"},
        }
        events = [
            {"event": "on_chain_start", "name": "LangGraph", "data": {"input": {}}},
            *_node_pair("alpha", graph_state),
            _final_chain_end(graph_state),
        ]
        agent = _GraphAgent(llm=mock_llm, events=events)
        result = await agent.run(
            messages=[HumanMessage(content="hi")],
            context={"paper_content": "p", "review_content": "r"},
            execution_id=uuid4(),
            progress_manager=None,
        )
        result["context"]["paper_content"] = "MUTATED"
        result["metadata"]["k"] = "MUTATED"
        assert graph_state["context"]["paper_content"] == "p"
        assert graph_state["metadata"]["k"] == "v"

    @pytest.mark.asyncio
    async def test_no_on_chain_end_with_dict_output_returns_input_state(self, mock_llm):
        events = [
            {"event": "on_chain_start", "name": "LangGraph", "data": {"input": {}}},
            {"event": "on_chain_end", "name": "LangGraph", "data": {"output": None}},
        ]
        agent = _GraphAgent(llm=mock_llm, events=events)
        with patch("app.agents.base.copy.deepcopy") as spy:
            await agent.run(
                messages=[HumanMessage(content="hi")],
                execution_id=uuid4(),
                progress_manager=None,
            )
        assert spy.call_count == 0


@pytest.mark.unit_db
class TestDeepCopyFallbackOnRuntimeError:
    """If deepcopy still raises (the symptom that motivated the fix), fall back."""

    @pytest.mark.asyncio
    async def test_falls_back_to_shallow_copy_when_deepcopy_raises(self, mock_llm):
        graph_state: dict[str, Any] = {
            "messages": [HumanMessage(content="hi")],
            "context": {"k": "v"},
            "output": "graph result",
            "metadata": {},
        }
        events = [
            {"event": "on_chain_start", "name": "LangGraph", "data": {"input": {}}},
            *_node_pair("alpha", graph_state),
            _final_chain_end(graph_state),
        ]

        def boom(_obj, *args, **kwargs):
            raise RuntimeError("dictionary changed size during iteration")

        agent = _GraphAgent(llm=mock_llm, events=events)
        with patch("app.agents.base.copy.deepcopy", side_effect=boom):
            result = await agent.run(
                messages=[HumanMessage(content="hi")],
                execution_id=uuid4(),
                progress_manager=None,
            )
        assert result is not graph_state
        assert result["context"]["k"] == "v"
        assert result["output"] == "graph result"
