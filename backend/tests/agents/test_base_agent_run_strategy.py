"""Regression tests for BaseAgent._run_strategy tools parameter forwarding.

Covers the falsy-fallback bug where ``tools=[]`` was treated the same as
``tools=None`` due to ``tools or self.tools`` short-circuiting on the
empty list.  The fix at ``base.py:142`` changed this to
``tools if tools is not None else self.tools``.
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.base import BaseAgent
from app.agents.strategies import AgentStrategy, EventType as StrategyEventType, StrategyEvent

pytestmark = pytest.mark.unit_db


class _RecordingStrategy(AgentStrategy):
    """Strategy that records the ``tools`` argument instead of calling the LLM.

    Each call to ``execute()`` appends a dict with the ``tools`` value to
    ``self.calls`` so tests can inspect what was forwarded.
    """

    max_iterations: int = 1

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def execute(
        self,
        llm: Any,
        messages: list[Any],
        system_prompt: str,
        tools: list[Any] | None = None,
    ) -> Any:  # returns AsyncIterator[StrategyEvent]
        self.calls.append({"tools": tools})
        yield StrategyEvent(
            type=StrategyEventType.STRATEGY_COMPLETE,
            phase="complete",
            iteration=1,
            max_iterations=1,
            result=AIMessage(content="recorded"),
        )


class _StrategyAgent(BaseAgent):
    """Minimal ``BaseAgent`` subclass used solely to exercise ``_run_strategy``.

    ``build_graph`` raises ``NotImplementedError`` because graph execution is
    never invoked when testing ``_run_strategy`` directly.
    """

    name = "test"
    description = "test agent"
    system_prompt = "test system prompt"

    def __init__(self, llm: Any, tools: list[Any] | None = None) -> None:
        super().__init__(llm=llm, strategy_name="direct", tools=tools)

    def build_graph(self) -> Any:
        raise NotImplementedError("not used — testing _run_strategy only")


def _make_agent(mock_llm: Any, *, agent_tools: list[Any] | None) -> tuple[_StrategyAgent, _RecordingStrategy]:
    """Build an agent and attach a recording strategy for inspection.

    Returns
    -------
    tuple[_StrategyAgent, _RecordingStrategy]
        The agent (with ``agent.strategy`` replaced) and the recorder
        (whose ``.calls`` list captures each ``execute()`` invocation).
    """
    agent = _StrategyAgent(llm=mock_llm, tools=agent_tools)
    recording = _RecordingStrategy()
    agent.strategy = recording
    return agent, recording


class TestRunStrategyToolsForwarding:
    """Regression tests for ``_run_strategy`` tools parameter forwarding."""

    async def test_explicit_empty_list_forwarded_not_replaced(
        self, mock_llm: Any
    ) -> None:
        """The bug: ``tools=[]`` must NOT be replaced by ``agent.tools``.

        Before the fix, ``tools or self.tools`` short-circuited on the falsy
        empty list and fell back to ``self.tools``.  After the fix,
        ``tools if tools is not None else self.tools`` preserves ``[]``.
        """
        agent_tools = [object(), object()]
        agent, recording = _make_agent(mock_llm, agent_tools=agent_tools)

        result = await agent._run_strategy(
            messages=[HumanMessage(content="hi")],
            tools=[],
        )

        assert isinstance(result, AIMessage)
        assert recording.calls[0]["tools"] == []

    async def test_default_none_falls_back_to_self_tools(
        self, mock_llm: Any
    ) -> None:
        """Omitting ``tools`` (default ``None``) falls back to ``agent.tools``."""
        agent_tools = [object()]
        agent, recording = _make_agent(mock_llm, agent_tools=agent_tools)

        result = await agent._run_strategy(
            messages=[HumanMessage(content="hi")],
        )

        assert isinstance(result, AIMessage)
        assert recording.calls[0]["tools"] is agent.tools

    async def test_explicit_none_falls_back_to_self_tools(
        self, mock_llm: Any
    ) -> None:
        """Explicit ``tools=None`` falls back to ``agent.tools``."""
        agent_tools = [object(), object()]
        agent, recording = _make_agent(mock_llm, agent_tools=agent_tools)

        result = await agent._run_strategy(
            messages=[HumanMessage(content="hi")],
            tools=None,
        )

        assert isinstance(result, AIMessage)
        assert recording.calls[0]["tools"] is agent.tools
