"""Chat agent — general-purpose conversational agent.

1-node pass-through graph, same as WritingAgent.  All LLM work is deferred
to the strategy (direct / critique / reflection) invoked by BaseAgent.run().
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.base import AgentState, BaseAgent


class ChatAgent(BaseAgent):
    """General-purpose chat agent for conversational academic assistance."""

    name = "chat"
    description = "General-purpose chat agent for conversational academic assistance."

    def build_graph(self) -> StateGraph:  # noqa: D102
        def pass_through(state: AgentState) -> AgentState:
            return state

        graph = StateGraph(AgentState)
        graph.add_node("pass_through", pass_through)
        graph.set_entry_point("pass_through")
        graph.add_edge("pass_through", END)
        return graph
