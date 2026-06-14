from abc import ABC, abstractmethod
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.agents.strategies import AgentStrategy, get_strategy


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
        self.strategy = get_strategy(strategy_name)
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

    async def run(
        self,
        messages: list[BaseMessage],
        context: dict[str, Any] | None = None,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        state = AgentState(
            messages=messages,
            context=context or {},
            output=None,
            metadata={"agent": self.name},
        )
        config = {"configurable": {"thread_id": thread_id or "default"}}
        result = await self.graph.ainvoke(state, config=config)
        return result
