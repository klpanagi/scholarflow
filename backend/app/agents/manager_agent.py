"""Manager agent — research project management agent.

1-node pass-through graph, same as WritingAgent / ChatAgent.  All LLM work is
deferred to the strategy (direct / critique / reflection) invoked by
BaseAgent.run().
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.base import AgentState, BaseAgent


class ManagerAgent(BaseAgent):
    """Research project management agent (work plans, milestones, budgets)."""

    name = "manager"
    description = "Research project management agent for work plans, milestones, and budgets."

    def build_graph(self) -> StateGraph:  # noqa: D102
        def pass_through(state: AgentState) -> AgentState:
            return state

        graph = StateGraph(AgentState)
        graph.add_node("pass_through", pass_through)
        graph.set_entry_point("pass_through")
        graph.add_edge("pass_through", END)
        return graph
