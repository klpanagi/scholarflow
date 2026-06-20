from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState


REVIEW_SYSTEM_PROMPT = """You are an expert academic paper reviewer. You evaluate papers rigorously, providing structured, evidence-based reviews.

Your review must include:
- **Summary**: Brief overview of the paper's contribution
- **Strengths**: Key positive aspects (3-5 points)
- **Weaknesses**: Key concerns (3-5 points)
- **Detailed Assessment**: Section-by-section analysis covering methodology, novelty, clarity, and reproducibility
- **Recommendations**: Specific actionable improvements
- **Decision**: Accept / Minor Revision / Major Revision / Reject

Be constructive, specific, and fair. Always cite evidence from the paper to support your assessments.
"""


class PaperReviewAgent(BaseAgent):
    name = "paper-review"
    description = "Lightweight paper review agent (2 LLM calls). Produces structured reviews with strengths, weaknesses, and recommendations."
    system_prompt = REVIEW_SYSTEM_PROMPT

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def analyze(state: AgentState) -> AgentState:
            messages = state["messages"]
            user_msg = messages[-1].content if messages else ""

            analysis_prompt = (
                "Analyze this paper and identify:\n"
                "1. Core contribution and novelty\n"
                "2. Methodology approach\n"
                "3. Key strengths and potential weaknesses\n"
                "4. Section structure and content quality\n\n"
                f"Paper content:\n{user_msg[:8000]}"
            )

            response = await self.strategy.execute(
                self.llm,
                messages[:-1] + [HumanMessage(content=analysis_prompt)],
                self.system_prompt,
            )
            state["context"]["analysis"] = response.content
            usage = getattr(response, "additional_kwargs", {}).get("usage")
            if usage:
                state["context"]["_usage"] = usage
            return state

        async def respond(state: AgentState) -> AgentState:
            analysis = state["context"].get("analysis", "")
            original_messages = state["messages"]

            review_prompt = (
                f"Based on your analysis:\n{analysis}\n\n"
                "Now produce a complete, structured academic review following this format:\n\n"
                "## Summary\n[Brief overview]\n\n"
                "## Strengths\n[3-5 numbered points]\n\n"
                "## Weaknesses\n[3-5 numbered points]\n\n"
                "## Detailed Assessment\n[Section-by-section analysis]\n\n"
                "## Recommendations for Authors\n[Specific improvements]\n\n"
                "## Decision\n[Accept / Minor Revision / Major Revision / Reject with justification]"
            )

            response = await self.strategy.execute(
                self.llm,
                original_messages + [HumanMessage(content=review_prompt)],
                self.system_prompt,
            )
            state["output"] = response.content
            usage = getattr(response, "additional_kwargs", {}).get("usage")
            if usage:
                existing = state["context"].get("_usage", {})
                if existing:
                    usage = {
                        "input_tokens": usage.get("input_tokens", 0) + existing.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0) + existing.get("output_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0) + existing.get("total_tokens", 0),
                    }
                state["context"]["_usage"] = usage
            return state

        graph.add_node("analyze", analyze)
        graph.add_node("respond", respond)

        graph.set_entry_point("analyze")
        graph.add_edge("analyze", "respond")
        graph.add_edge("respond", END)

        return graph
