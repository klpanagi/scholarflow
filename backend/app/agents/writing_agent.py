"""Writing agent — unified writer for all writer-type roles.

1-node pass-through graph.  All LLM work is deferred to Phase 2 of
``BaseAgent.run()`` which invokes the configured strategy (direct, critique,
etc.) with the system prompt and skills from AgentConfig.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.base import AgentState, BaseAgent


class WritingAgent(BaseAgent):
    """Unified writer agent.

    Produces text per AgentConfig (system_prompt + strategy + skills).
    The ``name`` field is ``"writer"``; user-facing display names such as
    ``"Review Writer"`` come from AgentConfig, not from this class.
    """

    name = "writing"
    description = "Unified writer agent. Produces text per AgentConfig (system_prompt + strategy + skills)."

    def build_graph(self) -> StateGraph:  # noqa: D102
        def pass_through(state: AgentState) -> AgentState:
            return state

        graph = StateGraph(AgentState)
        graph.add_node("pass_through", pass_through)
        graph.set_entry_point("pass_through")
        graph.add_edge("pass_through", END)
        return graph
