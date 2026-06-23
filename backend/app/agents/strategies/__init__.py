"""Agent execution strategies that yield typed intermediate events.

Each strategy is an :class:`AgentStrategy` subclass whose ``execute()`` method is
an ``async`` generator that yields :class:`StrategyEvent` instances. Subscribers
(e.g. a ``ProgressManager``) iterate over the events to publish progress without
blocking the LLM call. The final event has ``type == EventType.STRATEGY_COMPLETE``
and carries the final :class:`~langchain_core.messages.AIMessage` in
``event.result``.

The event taxonomy mirrors the Workflow Progress Visibility plan (see
``.matrixx/plans/workflow-progress-visibility.md`` "Event Taxonomy" section):
- ``strategy.iteration``  -- phase change inside a strategy (generate / critique / ...)
- ``strategy.complete``   -- final event with the AIMessage result
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    """Type of strategy event. String values match the SSE event taxonomy.

    String values mirror the ``event_type`` strings used by ProgressManager
    (see plan "Event Taxonomy" section). Using ``str, Enum`` makes the enum
    JSON-serializable while still allowing ``==`` comparisons against plain
    strings.
    """

    STRATEGY_ITERATION = "strategy.iteration"
    STRATEGY_COMPLETE = "strategy.complete"


class StrategyEvent(BaseModel):
    """A typed intermediate event emitted by a strategy.

    Fields
    ------
    type:
        Either :attr:`EventType.STRATEGY_ITERATION` (a phase within a strategy
        loop) or :attr:`EventType.STRATEGY_COMPLETE` (the final event carrying
        the :class:`AIMessage` result).
    phase:
        Human-readable phase name (``"generate"``, ``"critique"``, ``"refine"``,
        ``"reflect"``, ``"evaluate"``, ``"optimize"``, ``"complete"``).
    iteration:
        1-based loop counter for the current phase.
    max_iterations:
        Total number of outer iterations the strategy is configured for. For
        :class:`DirectStrategy` this is always ``1``.
    score:
        Optional numeric quality score (only set by :class:`EvaluatorOptimizerStrategy`
        on ``evaluate`` and ``optimize`` events).
    result:
        The final :class:`AIMessage` -- only set on the ``STRATEGY_COMPLETE``
        event. ``None`` for intermediate ``STRATEGY_ITERATION`` events.
    """

    type: EventType
    phase: str
    iteration: int
    max_iterations: int
    score: float | None = None
    # ``result`` is typed as ``Any`` rather than ``AIMessage | None`` to sidestep
    # a Pydantic v1/v2 interop bug: ``AIMessage`` (from langchain-core 1.x) still
    # defines a v1-style ``validate`` classmethod, which Pydantic v2 calls with
    # v2 arguments and crashes with "BaseModel.validate() takes 2 positional
    # arguments but 3 were given". The runtime contract is still "AIMessage on
    # STRATEGY_COMPLETE, None otherwise" -- tests assert ``isinstance(result, AIMessage)``.
    result: Any = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


def _extract_usage(response: AIMessage) -> dict[str, int]:
    """Extract token counts from an AIMessage's usage_metadata."""
    um = getattr(response, "usage_metadata", None) or {}
    return {
        "input_tokens": um.get("input_tokens", 0) or 0,
        "output_tokens": um.get("output_tokens", 0) or 0,
        "total_tokens": um.get("total_tokens", 0) or 0,
    }


def _merge_usage(acc: dict[str, int], usage: dict[str, int]) -> dict[str, int]:
    return {k: acc[k] + usage[k] for k in acc}


class AgentStrategy(ABC):
    """Abstract base for execution strategies.

    Subclasses must implement ``execute()`` as an ``async`` generator that yields
    :class:`StrategyEvent` instances. The generator must end with a single
    :attr:`EventType.STRATEGY_COMPLETE` event whose ``result`` is the final
    :class:`AIMessage` from the LLM.
    """

    #: Total iterations the strategy will run. Subclasses with configurable
    #: loops set this in ``__init__``; ``DirectStrategy`` is always ``1``.
    max_iterations: int = 1

    @abstractmethod
    def execute(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        system_prompt: str,
        tools: list[Any] | None = None,
    ) -> AsyncIterator[StrategyEvent]:
        """Run the strategy, yielding :class:`StrategyEvent` instances.

        Must end with one :attr:`EventType.STRATEGY_COMPLETE` event that
        carries the final :class:`AIMessage` in ``result``.
        """
        # Declared as a plain (non-async) method so the body becomes an
        # ``async def`` generator in subclasses. ABCMeta enforces that the
        # override is a coroutine function -- the runtime check on
        # instantiation catches any subclass that forgets the ``async`` keyword.
        ...


class DirectStrategy(AgentStrategy):
    """Single LLM call, no iteration. Emits exactly one ``STRATEGY_ITERATION``."""

    max_iterations: int = 1

    async def execute(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        system_prompt: str,
        tools: list[Any] | None = None,
    ) -> AsyncIterator[StrategyEvent]:
        all_messages = [SystemMessage(content=system_prompt)] + messages

        yield StrategyEvent(
            type=EventType.STRATEGY_ITERATION,
            phase="generate",
            iteration=1,
            max_iterations=self.max_iterations,
        )

        if tools:
            llm_with_tools = llm.bind_tools(tools)
            response = await llm_with_tools.ainvoke(all_messages)
        else:
            response = await llm.ainvoke(all_messages)
        response.additional_kwargs["usage"] = _extract_usage(response)

        yield StrategyEvent(
            type=EventType.STRATEGY_COMPLETE,
            phase="complete",
            iteration=1,
            max_iterations=self.max_iterations,
            result=response,
        )


class CritiqueStrategy(AgentStrategy):
    """Generate -> critique -> refine loop. 3 events per iteration."""

    def __init__(self, max_iterations: int = 1):
        self.max_iterations = max_iterations

    async def execute(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        system_prompt: str,
        tools: list[Any] | None = None,
    ) -> AsyncIterator[StrategyEvent]:
        all_messages = [SystemMessage(content=system_prompt)] + messages

        # Initial generate lives INSIDE the loop so the test contract "exactly
        # 3 events per iteration" holds even for max_iterations=1 (otherwise
        # we would emit 4 STRATEGY_ITERATION events: 1 generate + 1 critique
        # + 1 refine + 1 complete, contradicting the spec).
        acc: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        response: AIMessage | None = None
        for i in range(1, self.max_iterations + 1):
            yield StrategyEvent(
                type=EventType.STRATEGY_ITERATION,
                phase="generate",
                iteration=i,
                max_iterations=self.max_iterations,
            )
            response = await llm.ainvoke(all_messages)
            acc = _merge_usage(acc, _extract_usage(response))

            yield StrategyEvent(
                type=EventType.STRATEGY_ITERATION,
                phase="critique",
                iteration=i,
                max_iterations=self.max_iterations,
            )
            critique_prompt = (
                "Review the response above. Identify any weaknesses, inaccuracies, "
                "or areas for improvement. Be specific and constructive."
            )
            critique_messages = all_messages + [
                response,
                HumanMessage(content=critique_prompt),
            ]
            critique = await llm.ainvoke(critique_messages)
            acc = _merge_usage(acc, _extract_usage(critique))

            yield StrategyEvent(
                type=EventType.STRATEGY_ITERATION,
                phase="refine",
                iteration=i,
                max_iterations=self.max_iterations,
            )
            improve_messages = all_messages + [
                response,
                HumanMessage(
                    content=f"Based on this critique, improve your response:\n\n{critique.content}"
                ),
            ]
            response = await llm.ainvoke(improve_messages)
            acc = _merge_usage(acc, _extract_usage(response))

        assert response is not None  # guaranteed by the loop above when max_iterations >= 1
        response.additional_kwargs["usage"] = acc
        yield StrategyEvent(
            type=EventType.STRATEGY_COMPLETE,
            phase="complete",
            iteration=self.max_iterations,
            max_iterations=self.max_iterations,
            result=response,
        )


class ReflectionStrategy(AgentStrategy):
    """Generate -> reflect loop. 2 events per iteration."""

    def __init__(self, max_iterations: int = 1):
        self.max_iterations = max_iterations

    async def execute(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        system_prompt: str,
        tools: list[Any] | None = None,
    ) -> AsyncIterator[StrategyEvent]:
        all_messages = [SystemMessage(content=system_prompt)] + messages

        acc: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        response: AIMessage | None = None
        for i in range(1, self.max_iterations + 1):
            yield StrategyEvent(
                type=EventType.STRATEGY_ITERATION,
                phase="generate",
                iteration=i,
                max_iterations=self.max_iterations,
            )
            response = await llm.ainvoke(all_messages)
            acc = _merge_usage(acc, _extract_usage(response))

            yield StrategyEvent(
                type=EventType.STRATEGY_ITERATION,
                phase="reflect",
                iteration=i,
                max_iterations=self.max_iterations,
            )
            reflection_prompt = (
                f"Reflect on this response:\n\n{response.content}\n\n"
                "What could be improved? What's missing? What's incorrect? "
                "Then provide a revised, improved response."
            )
            reflection_messages = all_messages + [HumanMessage(content=reflection_prompt)]
            response = await llm.ainvoke(reflection_messages)
            acc = _merge_usage(acc, _extract_usage(response))

        assert response is not None  # guaranteed by the loop above when max_iterations >= 1
        response.additional_kwargs["usage"] = acc
        yield StrategyEvent(
            type=EventType.STRATEGY_COMPLETE,
            phase="complete",
            iteration=self.max_iterations,
            max_iterations=self.max_iterations,
            result=response,
        )


class EvaluatorOptimizerStrategy(AgentStrategy):
    """Generate -> (evaluate -> maybe optimize) loop. Score reported on events."""

    def __init__(self, max_iterations: int = 2, quality_threshold: float = 0.8):
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold

    async def execute(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        system_prompt: str,
        tools: list[Any] | None = None,
    ) -> AsyncIterator[StrategyEvent]:
        all_messages = [SystemMessage(content=system_prompt)] + messages

        yield StrategyEvent(
            type=EventType.STRATEGY_ITERATION,
            phase="generate",
            iteration=1,
            max_iterations=self.max_iterations,
        )
        current_best = await llm.ainvoke(all_messages)
        acc = _extract_usage(current_best)

        score = 0.0
        for i in range(1, self.max_iterations + 1):
            eval_prompt = (
                f"Evaluate this response on a scale of 0.0 to 1.0 for quality, "
                f"accuracy, and completeness:\n\n{current_best.content}\n\n"
                "Respond with ONLY a number between 0.0 and 1.0."
            )
            eval_messages = all_messages + [HumanMessage(content=eval_prompt)]
            eval_response = await llm.ainvoke(eval_messages)
            acc = _merge_usage(acc, _extract_usage(eval_response))

            try:
                # AIMessage.content is typed as ``str | list[str | dict]``; we
                # only care about the string branch here (LLMs are instructed
                # to return "ONLY a number"), but the type narrowing keeps
                # pyright happy and makes the runtime fallback explicit.
                raw_content = eval_response.content
                if isinstance(raw_content, str):
                    score = float(raw_content.strip())
                else:
                    score = 0.0
            except (ValueError, AttributeError):
                score = 0.0

            # Emit the evaluate event WITH the score so subscribers can
            # forward quality numbers to the UI.
            yield StrategyEvent(
                type=EventType.STRATEGY_ITERATION,
                phase="evaluate",
                iteration=i,
                max_iterations=self.max_iterations,
                score=score,
            )

            if score >= self.quality_threshold:
                break

            yield StrategyEvent(
                type=EventType.STRATEGY_ITERATION,
                phase="optimize",
                iteration=i,
                max_iterations=self.max_iterations,
                score=score,
            )
            optimize_prompt = (
                f"The current response scored {score}. Improve it to be more "
                f"accurate, complete, and high-quality:\n\n{current_best.content}"
            )
            optimize_messages = all_messages + [HumanMessage(content=optimize_prompt)]
            current_best = await llm.ainvoke(optimize_messages)
            acc = _merge_usage(acc, _extract_usage(current_best))

        current_best.additional_kwargs["usage"] = acc
        yield StrategyEvent(
            type=EventType.STRATEGY_COMPLETE,
            phase="complete",
            iteration=self.max_iterations,
            max_iterations=self.max_iterations,
            score=score,
            result=current_best,
        )


STRATEGIES: dict[str, type[AgentStrategy]] = {
    "direct": DirectStrategy,
    "critique": CritiqueStrategy,
    "reflection": ReflectionStrategy,
    "evaluator_optimizer": EvaluatorOptimizerStrategy,
}


def get_strategy(name: str, **kwargs) -> AgentStrategy:
    """Instantiate a strategy by registered name.

    Unknown names raise :class:`ValueError`. Pass strategy-specific kwargs
    (e.g. ``max_iterations``, ``quality_threshold``) to configure the
    underlying class.
    """
    strategy_cls = STRATEGIES.get(name)
    if not strategy_cls:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return strategy_cls(**kwargs)
