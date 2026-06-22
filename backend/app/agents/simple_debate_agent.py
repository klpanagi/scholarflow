"""Simple debate agent: 2-node graph (intake -> respond).

Lightweight adversarial debate pipeline that stress-tests review criticisms
against paper evidence. 2 LLM calls, ~20K tokens.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.base import AgentState, BaseAgent


SIMPLE_DEBATE_PROMPT = """You are an expert academic debate moderator. You produce a structured debate analysis stress-testing review criticisms against paper evidence.

Your output must include these three sections:
- **Paper Defense**: For each major criticism, present the paper's strongest possible defense with specific evidence
- **Review Rebuttal**: Evaluate each defense — is the evidence sufficient? Are there gaps?
- **Balanced Synthesis**: Resolve disagreements, provide a final recommendation (Accept / Minor Revision / Major Revision / Reject)

Be balanced, specific, and evidence-based. Cite paper sections or figures when possible."""


class SimpleDebateAgent(BaseAgent):
    """2-node debate pipeline: intake -> respond.

    Lightweight adversarial debate for short turnaround. 2 LLM calls, ~20K tokens.
    """

    name = "simple-debate"
    description = "2-node debate pipeline (intake->respond). 2 LLM calls, ~20K tokens."
    system_prompt = SIMPLE_DEBATE_PROMPT

    async def _invoke_with_usage(self, state, messages, accumulate=True):
        """Invoke the LLM and accumulate token usage into the state context.

        Pattern from DeepReviewAgent (``app/agents/review_pipeline.py:59-72``):
        reads ``usage_metadata`` directly from the AIMessage.
        """
        response = await self.llm.ainvoke(messages)
        if accumulate and state is not None:
            um = getattr(response, "usage_metadata", None) or {}
            usage = {
                "input_tokens": um.get("input_tokens", 0) or 0,
                "output_tokens": um.get("output_tokens", 0) or 0,
                "total_tokens": um.get("total_tokens", 0) or 0,
            }
            acc = state["context"].get(
                "_usage",
                {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            )
            state["context"]["_usage"] = {k: acc[k] + usage[k] for k in acc}
        return response

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def intake(state: AgentState) -> AgentState:
            paper_content = state["context"].get("paper_content", "")
            review_content = state["context"].get("review_content", "")
            state["context"]["parsed_input"] = {
                "paper_content": paper_content,
                "review_content": review_content,
            }
            return state

        async def respond(state: AgentState) -> AgentState:
            parsed = state["context"].get("parsed_input", {})
            paper = parsed.get("paper_content", "")
            review = parsed.get("review_content", "")

            initial_messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=(
                    f"Paper:\n{paper}\n\n"
                    f"Review:\n{review}\n\n"
                    "Produce the initial debate analysis with 'Paper Defense' and "
                    "'Review Rebuttal' sections."
                )),
            ]
            initial_response = await self._invoke_with_usage(state, initial_messages)
            state["context"]["debate"] = initial_response.content

            synthesis_messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=(
                    f"Paper:\n{paper}\n\n"
                    f"Review:\n{review}\n\n"
                    f"Initial debate analysis:\n{initial_response.content}\n\n"
                    "Now produce the final 'Balanced Synthesis' section with a "
                    "recommendation (Accept / Minor Revision / Major Revision / Reject). "
                    "Include all three sections (Paper Defense, Review Rebuttal, "
                    "Balanced Synthesis) in your final output."
                )),
            ]
            synthesis_response = await self._invoke_with_usage(state, synthesis_messages)
            state["output"] = synthesis_response.content

            return state

        graph.add_node("intake", intake)
        graph.add_node("respond", respond)
        graph.set_entry_point("intake")
        graph.add_edge("intake", "respond")
        graph.add_edge("respond", END)

        return graph
