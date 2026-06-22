"""Deep debate agent: 4-node graph (intake → defend_paper → evaluate_defense → synthesize).

Thorough adversarial review with dedicated paper defense, defense evaluation,
and neutral synthesis stages. 3 LLM calls, ~40K tokens.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState


DEEP_DEBATE_SYSTEM_PROMPT = """You are an expert academic debate moderator running a thorough adversarial review process.

You orchestrate a 3-stage debate (after intake):
1. **Paper Advocate** (defend_paper): Defend the paper against each criticism with specific evidence
2. **Review Advocate** (evaluate_defense): Critically evaluate whether the defense is substantiated, identify gaps
3. **Neutral Moderator** (synthesize): Combine defense + evaluation into balanced final assessment

Be rigorous, evidence-based, and fair. Cite specific paper sections, figures, and results. Never fabricate evidence. Acknowledge when a criticism is valid."""


class DeepDebateAgent(BaseAgent):
    """4-node deep debate pipeline: intake → defend_paper → evaluate_defense → synthesize.

    Thorough adversarial review with dedicated defense and evaluation stages.
    3 LLM calls, ~40K tokens.
    """

    name = "deep-debate"
    description = (
        "4-node deep debate pipeline (intake→defend-paper→evaluate-defense→synthesize). "
        "3 LLM calls, ~40K tokens."
    )
    system_prompt = DEEP_DEBATE_SYSTEM_PROMPT

    async def _invoke_with_usage(
        self, state: AgentState | None, messages: list, accumulate: bool = True
    ):
        response = await self.llm.ainvoke(messages)
        if accumulate and state is not None:
            um = getattr(response, "usage_metadata", None) or {}
            usage = {
                "input_tokens": um.get("input_tokens", 0) or 0,
                "output_tokens": um.get("output_tokens", 0) or 0,
                "total_tokens": um.get("total_tokens", 0) or 0,
            }
            acc = state["context"].get(
                "_usage", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
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

        async def defend_paper(state: AgentState) -> AgentState:
            parsed = state["context"].get("parsed_input", {})
            paper = parsed.get("paper_content", "")
            review = parsed.get("review_content", "")

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(
                    content=(
                        f"STAGE 1: PAPER DEFENSE\n\n"
                        f"You are the Paper Advocate. Defend the paper against each criticism in the review.\n\n"
                        f"Paper:\n{paper}\n\n"
                        f"Review:\n{review}\n\n"
                        "For each major criticism:\n"
                        "1. State the criticism\n"
                        "2. Present the paper's strongest defense with specific evidence\n"
                        "3. Acknowledge valid criticisms and suggest improvements\n\n"
                        "OUTPUT FORMAT:\n"
                        "## Paper Defense\n[Point-by-point defense with evidence]"
                    )
                ),
            ]

            response = await self._invoke_with_usage(state, messages)
            state["context"]["paper_defense"] = response.content
            return state

        async def evaluate_defense(state: AgentState) -> AgentState:
            paper_defense = state["context"].get("paper_defense", "")
            parsed = state["context"].get("parsed_input", {})
            review = parsed.get("review_content", "")

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(
                    content=(
                        f"STAGE 2: DEFENSE EVALUATION\n\n"
                        f"You are the Review Advocate. Evaluate whether the paper's defense is substantiated.\n\n"
                        f"Original Review:\n{review}\n\n"
                        f"Paper Defense:\n{paper_defense}\n\n"
                        "For each defense point, assess:\n"
                        "1. Does the defense actually address the criticism?\n"
                        "2. Is the evidence cited relevant and sufficient?\n"
                        "3. Are there gaps in the defense?\n\n"
                        "OUTPUT FORMAT:\n"
                        "## Defense Evaluation\n[Point-by-point assessment: supported / partially supported / not supported]"
                    )
                ),
            ]

            response = await self._invoke_with_usage(state, messages)
            state["context"]["defense_evaluation"] = response.content
            return state

        async def synthesize(state: AgentState) -> AgentState:
            paper_defense = state["context"].get("paper_defense", "")
            defense_evaluation = state["context"].get("defense_evaluation", "")

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(
                    content=(
                        f"STAGE 3: NEUTRAL SYNTHESIS\n\n"
                        f"Combine the paper defense and defense evaluation into a balanced final assessment.\n\n"
                        f"Paper Defense:\n{paper_defense}\n\n"
                        f"Defense Evaluation:\n{defense_evaluation}\n\n"
                        "Provide:\n"
                        "1. Points of agreement\n"
                        "2. Resolved disagreements with your assessment\n"
                        "3. **Final Recommendation**: Accept / Minor Revision / Major Revision / Reject\n"
                        "4. Required revisions list"
                    )
                ),
            ]

            response = await self._invoke_with_usage(state, messages)
            state["output"] = response.content
            return state

        graph.add_node("intake", intake)
        graph.add_node("defend_paper", defend_paper)
        graph.add_node("evaluate_defense", evaluate_defense)
        graph.add_node("synthesize", synthesize)
        graph.set_entry_point("intake")
        graph.add_edge("intake", "defend_paper")
        graph.add_edge("defend_paper", "evaluate_defense")
        graph.add_edge("evaluate_defense", "synthesize")
        graph.add_edge("synthesize", END)

        return graph
