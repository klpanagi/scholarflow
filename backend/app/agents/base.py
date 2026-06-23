"""Base agent class — graph + strategy orchestration with progress streaming.

The :class:`BaseAgent.run()` method is the single entry point used by
``_run_stage`` in ``app/api/routes/workflows.py``. It does two things:

1. **Graph streaming** — calls ``self.graph.astream_events(state, ..., version="v2")``
   so we can observe every node and tool call. When a ``ProgressManager`` and
   ``execution_id`` are provided, we publish ``NODE_STARTED``, ``NODE_COMPLETED``,
   ``TOOL_CALL`` and ``TOOL_COMPLETE`` events as the graph runs.

2. **Strategy wrapping** — once the graph finishes, we run the agent's
   strategy (an async generator of :class:`StrategyEvent`) IF the graph did
   not already produce a final output. The strategy's
   ``STRATEGY_ITERATION`` events are published to the progress stream; the
   final ``STRATEGY_COMPLETE`` event carries the wrapping ``AIMessage``.

The strategy is skipped when the graph already set ``state["output"]`` —
this preserves backward compatibility with existing agents like
:class:`DebateAgent` whose synthesize node produces the final response.
The strategy is the fallback for agents whose graphs only do pre-processing.

Cancellation is observed at the top of each graph event: when the
``_cancel_flags`` singleton has a flag set for the ``execution_id``, the
streaming loop breaks and the agent returns whatever state has been
captured so far.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.strategies import (
    AgentStrategy,
    EventType as StrategyEventType,
    get_strategy,
)
from app.services.progress import (
    EventType as ProgressEventType,
    ExecutionEvent,
    ProgressManager,
)

logger = logging.getLogger(__name__)

# Cap the size of a tool input snippet we forward in TOOL_CALL events. The
# full input is in the LangGraph state — we just truncate for the SSE payload
# to keep event JSON small.
_TOOL_INPUT_MAX_CHARS = 200


class AgentState(dict):
    messages: list[BaseMessage]
    context: dict[str, Any]
    output: Any
    metadata: dict[str, Any]


class BaseAgent(ABC):
    name: str
    description: str
    system_prompt: str

    def __init__(
        self,
        llm: BaseChatModel,
        strategy_name: str = "direct",
        tools: list[Any] | None = None,
        system_prompt: str | None = None,
    ):
        self.llm = llm
        self.tools = tools or []
        self.strategy: AgentStrategy = get_strategy(strategy_name)
        self._graph: CompiledStateGraph | None = None
        if system_prompt:
            self.system_prompt = system_prompt

    @abstractmethod
    def build_graph(self) -> StateGraph:
        ...

    @property
    def graph(self) -> CompiledStateGraph:
        if self._graph is None:
            graph = self.build_graph()
            memory = MemorySaver()
            self._graph = graph.compile(checkpointer=memory)
        return self._graph

    async def _publish_event(
        self,
        progress_manager: ProgressManager,
        execution_id: UUID | str,
        event_type: ProgressEventType,
        data: dict[str, Any],
    ) -> None:
        """Publish a metadata-only event with a manager-assigned monotonic id.

        The manager's ``_next_id`` is private API, so we go through the
        ``_next_progress_event_id`` helper in ``app.api.routes.workflows``
        (which acquires the per-execution lock before reading the counter).
        Lazy import avoids pulling FastAPI into the agents module at load time.
        """
        from app.api.routes.workflows import _next_progress_event_id

        event_id = await _next_progress_event_id(progress_manager, execution_id)
        event = ExecutionEvent(
            event_id=event_id,
            execution_id=UUID(str(execution_id)),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            data=data,
        )
        await progress_manager.publish(execution_id, event)

    async def _run_strategy(
        self,
        messages: list[BaseMessage],
        tools: list[Any] | None = None,
    ) -> AIMessage:
        """Execute the agent's strategy and return the final response.

        Properly iterates the async generator to collect the result.
        The strategy is responsible for attaching usage metadata to
        response.additional_kwargs["usage"].
        """
        async for event in self.strategy.execute(
            self.llm,
            messages,
            self.system_prompt,
            tools or self.tools,
        ):
            if event.type is StrategyEventType.STRATEGY_COMPLETE:
                if event.result is not None:
                    return event.result
        raise RuntimeError(
            f"Strategy '{self.strategy.__class__.__name__}' completed "
            "without producing a result"
        )

    async def run(
        self,
        messages: list[BaseMessage],
        context: dict[str, Any] | None = None,
        thread_id: str | None = None,
        progress_manager: ProgressManager | None = None,
        execution_id: UUID | str | None = None,
    ) -> dict[str, Any]:
        """Run the agent: graph streaming + optional strategy wrapping.

        Returns the final state dict with ``messages``, ``context``,
        ``output`` and ``metadata`` keys — matching the pre-Task-6 contract.

        The two optional kwargs ``progress_manager`` and ``execution_id``
        are both required to enable event publishing. Either being ``None``
        disables publishing (preserves existing call sites and tests that
        don't care about progress events).
        """
        state = AgentState(
            messages=list(messages),
            context=context or {},
            output=None,
            metadata={"agent": self.name},
        )
        config: RunnableConfig = {"configurable": {"thread_id": thread_id or "default"}}

        # Lazy import — the cancel flags singleton lives in the workflows
        # route module, which depends on FastAPI. We don't want to import
        # that at agent module load time.
        from app.api.routes.workflows import _cancel_flags

        # ------------------------------------------------------------------
        # Phase 1: Graph streaming with astream_events
        # ------------------------------------------------------------------
        # Map node_name -> monotonic start time so we can compute durations
        # when the matching on_chain_end fires. The root graph ("LangGraph")
        # is excluded from this map.
        node_starts: dict[str, float] = {}
        # Track the last seen final state. In LangGraph's v2 events the root
        # ``on_chain_end`` has ``data.output`` = final state. Any intermediate
        # on_chain_end with a dict ``data.output`` is also captured — the last
        # one wins.
        final_state: dict[str, Any] = state

        async for ev in self.graph.astream_events(state, config=config, version="v2"):
            # Cancellation: checked at the TOP of each iteration so a
            # cancel request that arrives mid-stream interrupts the loop
            # at the next event boundary (per the "no cancellation inside
            # the strategy loop" rule in the task spec).
            if execution_id is not None and _cancel_flags.get(str(execution_id), False):
                break

            if progress_manager is not None and execution_id is not None:
                kind = ev.get("event", "")
                name = ev.get("name", "")

                if (
                    kind == "on_chain_start"
                    and name
                    and not name.startswith("__")
                    and name != "LangGraph"
                ):
                    node_starts[name] = time.monotonic()
                    await self._publish_event(
                        progress_manager,
                        execution_id,
                        ProgressEventType.NODE_STARTED,
                        {"node_name": name, "agent_type": self.name},
                    )

                elif kind == "on_chain_end" and name in node_starts:
                    start_ts = node_starts.pop(name)
                    duration_ms = int((time.monotonic() - start_ts) * 1000)
                    await self._publish_event(
                        progress_manager,
                        execution_id,
                        ProgressEventType.NODE_COMPLETED,
                        {
                            "node_name": name,
                            "duration_ms": duration_ms,
                            "status": "completed",
                        },
                    )

                elif kind == "on_tool_start":
                    tool_name = name or "<unknown>"
                    tool_input = (ev.get("data") or {}).get("input", {})
                    input_str = str(tool_input)
                    if len(input_str) > _TOOL_INPUT_MAX_CHARS:
                        input_str = input_str[:_TOOL_INPUT_MAX_CHARS] + "..."
                    await self._publish_event(
                        progress_manager,
                        execution_id,
                        ProgressEventType.TOOL_CALL,
                        {"tool_name": tool_name, "input_truncated": input_str},
                    )

                elif kind == "on_tool_end":
                    tool_name = name or "<unknown>"
                    await self._publish_event(
                        progress_manager,
                        execution_id,
                        ProgressEventType.TOOL_COMPLETE,
                        {"tool_name": tool_name, "status": "completed"},
                    )

            # Capture the final state from any on_chain_end whose data.output
            # looks like a state dict. The LAST such event in the stream is
            # the root graph's final state (per LangGraph v2 semantics).
            if ev.get("event") == "on_chain_end":
                data = ev.get("data") or {}
                output = data.get("output")
                if isinstance(output, dict):
                    final_state = output

        # ------------------------------------------------------------------
        # Phase 2: Strategy wrapping
        # ------------------------------------------------------------------
        # Only invoke the strategy when the graph didn't already produce a
        # final output. This preserves backward compatibility with agents
        # like DebateAgent whose synthesize node sets ``state["output"]`` —
        # the strategy is a no-op for them, so existing tests that assert
        # exact LLM call counts continue to pass.
        # Skip the strategy if the execution has been cancelled — the graph
        # stream's cancel check already stopped further graph events, and
        # running the strategy would publish STRATEGY_ITERATION events for
        # an already-cancelled execution.
        cancelled = (
            execution_id is not None
            and _cancel_flags.get(str(execution_id), False)
        )
        if not cancelled and not final_state.get("output") and self.strategy is not None:
            graph_messages = list(final_state.get("messages", []))
            async for sev in self.strategy.execute(
                self.llm, graph_messages, self.system_prompt, self.tools
            ):
                if progress_manager is not None and execution_id is not None:
                    if sev.type is StrategyEventType.STRATEGY_ITERATION:
                        await self._publish_event(
                            progress_manager,
                            execution_id,
                            ProgressEventType.STRATEGY_ITERATION,
                            {
                                "phase": sev.phase,
                                "iteration": sev.iteration,
                                "max_iterations": sev.max_iterations,
                                "score": sev.score,
                            },
                        )
                if sev.type is StrategyEventType.STRATEGY_COMPLETE:
                    response = sev.result
                    if response is not None:
                        existing_messages = list(final_state.get("messages", []))
                        existing_messages.append(response)
                        final_state["messages"] = existing_messages
                        content = getattr(response, "content", None)
                        if isinstance(content, str):
                            final_state["output"] = content
                        elif content is not None:
                            final_state["output"] = str(content)

        # ------------------------------------------------------------------
        # Usage extraction (matches the pre-Task-6 behaviour)
        # ------------------------------------------------------------------
        usage = final_state.get("context", {}).get("_usage")
        if not usage:
            for msg in reversed(final_state.get("messages", [])):
                if (
                    hasattr(msg, "additional_kwargs")
                    and "usage" in msg.additional_kwargs
                ):
                    usage = msg.additional_kwargs["usage"]
                    break
        if usage:
            metadata = final_state.setdefault("metadata", {})
            if isinstance(metadata, dict):
                metadata["usage"] = usage

        return final_state
