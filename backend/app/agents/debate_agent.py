"""Standard debate agent: 3-node graph (intake → debate → synthesize).

Runs structured adversarial debate with Paper Advocate (defense) and
Review Advocate (critique) positions, then synthesizes balanced assessment.
3 LLM calls, ~30K tokens.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState


DEBATE_SYSTEM_PROMPT = """You are an expert academic debate moderator running structured adversarial debates to stress-test academic work.

You are neutral but rigorous. For each turn:
- Present BOTH sides fairly (Paper Advocate defends, Review Advocate critiques)
- Cite specific evidence from the document under review
- Avoid sycophancy — identify where the paper genuinely has weaknesses
- Provide balanced final assessment with clear recommendations

OUTPUT FORMAT — Each debate stage must include:
- **Paper Advocate**: Strongest defense of the paper against the criticism with evidence
- **Review Advocate**: Strongest critique of the paper with specific weaknesses
- **Moderator Note**: Your balanced observation of which side is more credible here"""


class DebateAgent(BaseAgent):
    """3-node debate pipeline: intake → debate → synthesize.

    Standard adversarial debate. 3 LLM calls, ~30K tokens.
    """

    name = "debate"
    description = "3-node debate pipeline (intake→debate→synthesize). 3 LLM calls, ~30K tokens."
    system_prompt = DEBATE_SYSTEM_PROMPT

    async def _invoke_with_usage(self, state, messages, accumulate=True):
        response = await self.llm.ainvoke(messages)
        if accumulate and state is not None:
            um = getattr(response, "usage_metadata", None) or {}
            usage = {
                "input_tokens": um.get("input_tokens", 0) or 0,
                "output_tokens": um.get("output_tokens", 0) or 0,
                "total_tokens": um.get("total_tokens", 0) or 0,
            }
            acc = state["context"].get("_usage", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
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

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=(
                    f"Stage 0: INTAKE\n\n"
                    f"Extract the key claims, contributions, and criticisms from this paper and review pair. "
                    f"Identify the main points of disagreement that the debate should focus on.\n\n"
                    f"Paper:\n{paper_content}\n\n"
                    f"Review:\n{review_content}"
                )),
            ]

            response = await self._invoke_with_usage(state, messages)
            state["context"]["intake"] = response.content
            return state

        async def debate(state: AgentState) -> AgentState:
            parsed = state["context"].get("parsed_input", {})
            paper = parsed.get("paper_content", "")
            review = parsed.get("review_content", "")

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=(
                    f"Run an adversarial debate on this paper and review.\n\n"
                    f"Paper:\n{paper}\n\n"
                    f"Review:\n{review}\n\n"
                    "For each major criticism, present:\n"
                    "1. **Paper Advocate**: defense with evidence from the paper\n"
                    "2. **Review Advocate**: critique with specific weaknesses\n"
                    "3. **Moderator Note**: balanced observation"
                )),
            ]

            response = await self._invoke_with_usage(state, messages)
            state["context"]["debate_positions"] = response.content
            return state

        async def synthesize(state: AgentState) -> AgentState:
            debate_output = state["context"].get("debate_positions", "")

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=(
                    f"Synthesize the following debate into a balanced final assessment.\n\n"
                    f"Debate:\n{debate_output}\n\n"
                    "Provide:\n"
                    "1. Points of agreement between Paper and Review advocates\n"
                    "2. Your resolution of disagreements\n"
                    "3. **Final Synthesis** with Accept / Minor Revision / Major Revision / Reject recommendation"
                )),
            ]

            response = await self._invoke_with_usage(state, messages)
            state["output"] = response.content
            return state

        graph.add_node("intake", intake)
        graph.add_node("debate", debate)
        graph.add_node("synthesize", synthesize)
        graph.set_entry_point("intake")
        graph.add_edge("intake", "debate")
        graph.add_edge("debate", "synthesize")
        graph.add_edge("synthesize", END)

        return graph
