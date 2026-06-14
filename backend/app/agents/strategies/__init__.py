from abc import ABC, abstractmethod
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage


class AgentStrategy(ABC):
    @abstractmethod
    async def execute(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        system_prompt: str,
        tools: list[Any] | None = None,
    ) -> AIMessage:
        ...


class DirectStrategy(AgentStrategy):
    async def execute(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        system_prompt: str,
        tools: list[Any] | None = None,
    ) -> AIMessage:
        all_messages = [SystemMessage(content=system_prompt)] + messages
        if tools:
            llm_with_tools = llm.bind_tools(tools)
            return await llm_with_tools.ainvoke(all_messages)
        return await llm.ainvoke(all_messages)


class CritiqueStrategy(AgentStrategy):
    def __init__(self, max_iterations: int = 1):
        self.max_iterations = max_iterations

    async def execute(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        system_prompt: str,
        tools: list[Any] | None = None,
    ) -> AIMessage:
        all_messages = [SystemMessage(content=system_prompt)] + messages
        response = await llm.ainvoke(all_messages)

        critique_prompt = (
            "Review the response above. Identify any weaknesses, inaccuracies, "
            "or areas for improvement. Be specific and constructive."
        )

        for _ in range(self.max_iterations):
            critique_messages = all_messages + [
                response,
                HumanMessage(content=critique_prompt),
            ]
            critique = await llm.ainvoke(critique_messages)

            improve_messages = all_messages + [
                response,
                HumanMessage(content=f"Based on this critique, improve your response:\n\n{critique.content}"),
            ]
            response = await llm.ainvoke(improve_messages)

        return response


class ReflectionStrategy(AgentStrategy):
    def __init__(self, max_iterations: int = 1):
        self.max_iterations = max_iterations

    async def execute(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        system_prompt: str,
        tools: list[Any] | None = None,
    ) -> AIMessage:
        all_messages = [SystemMessage(content=system_prompt)] + messages
        response = await llm.ainvoke(all_messages)

        for _ in range(self.max_iterations):
            reflection_prompt = (
                f"Reflect on this response:\n\n{response.content}\n\n"
                "What could be improved? What's missing? What's incorrect? "
                "Then provide a revised, improved response."
            )
            reflection_messages = all_messages + [HumanMessage(content=reflection_prompt)]
            response = await llm.ainvoke(reflection_messages)

        return response


class EvaluatorOptimizerStrategy(AgentStrategy):
    def __init__(self, max_iterations: int = 2, quality_threshold: float = 0.8):
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold

    async def execute(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        system_prompt: str,
        tools: list[Any] | None = None,
    ) -> AIMessage:
        all_messages = [SystemMessage(content=system_prompt)] + messages
        current_best = await llm.ainvoke(all_messages)

        for _ in range(self.max_iterations):
            eval_prompt = (
                f"Evaluate this response on a scale of 0.0 to 1.0 for quality, "
                f"accuracy, and completeness:\n\n{current_best.content}\n\n"
                "Respond with ONLY a number between 0.0 and 1.0."
            )
            eval_messages = all_messages + [HumanMessage(content=eval_prompt)]
            eval_response = await llm.ainvoke(eval_messages)

            try:
                score = float(eval_response.content.strip())
            except ValueError:
                score = 0.0

            if score >= self.quality_threshold:
                break

            optimize_prompt = (
                f"The current response scored {score}. Improve it to be more "
                f"accurate, complete, and high-quality:\n\n{current_best.content}"
            )
            optimize_messages = all_messages + [HumanMessage(content=optimize_prompt)]
            current_best = await llm.ainvoke(optimize_messages)

        return current_best


STRATEGIES: dict[str, type[AgentStrategy]] = {
    "direct": DirectStrategy,
    "critique": CritiqueStrategy,
    "reflection": ReflectionStrategy,
    "evaluator_optimizer": EvaluatorOptimizerStrategy,
}


def get_strategy(name: str, **kwargs) -> AgentStrategy:
    strategy_cls = STRATEGIES.get(name)
    if not strategy_cls:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return strategy_cls(**kwargs)
