from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState


class ReviewAgent(BaseAgent):
    name = "review"
    description = "Provide detailed peer review feedback on academic papers"
    system_prompt = (
        "You are an expert academic peer reviewer. You provide thorough, "
        "constructive feedback on research papers.\n\n"
        "Your review should cover:\n"
        "- Originality and contribution to the field\n"
        "- Methodology soundness\n"
        "- Clarity of presentation\n"
        "- Strength of evidence and arguments\n"
        "- Limitations and potential improvements\n"
        "- Relevance to the target venue\n\n"
        "Be constructive and specific. Cite page/section numbers when possible."
    )

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def analyze_paper(state: AgentState) -> AgentState:
            messages = state["messages"]
            user_msg = messages[-1].content if messages else ""

            analysis_prompt = (
                f"Analyze the paper content provided and identify:\n"
                f"1. Main claims and contributions\n"
                f"2. Methodology approach\n"
                f"3. Key strengths\n"
                f"4. Obvious weaknesses or gaps\n\n"
                f"Paper content:\n{user_msg}"
            )

            response = await self.strategy.execute(
                self.llm,
                messages[:-1] + [HumanMessage(content=analysis_prompt)],
                self.system_prompt,
            )
            state["context"]["paper_analysis"] = response.content
            return state

        async def generate_review(state: AgentState) -> AgentState:
            paper_analysis = state["context"].get("paper_analysis", "")

            review_prompt = (
                f"Based on the analysis:\n{paper_analysis}\n\n"
                f"Generate a structured peer review with:\n"
                f"1. Summary (1 paragraph)\n"
                f"2. Major concerns (numbered list)\n"
                f"3. Minor concerns (numbered list)\n"
                f"4. Questions for authors\n"
                f"5. Overall recommendation (Accept/Weak Accept/Weak Reject/Reject)\n"
                f"6. Confidence level (1-5)"
            )

            response = await self.strategy.execute(
                self.llm,
                state["messages"] + [HumanMessage(content=review_prompt)],
                self.system_prompt,
            )
            state["output"] = response.content
            return state

        graph.add_node("analyze_paper", analyze_paper)
        graph.add_node("generate_review", generate_review)

        graph.set_entry_point("analyze_paper")
        graph.add_edge("analyze_paper", "generate_review")
        graph.add_edge("generate_review", END)

        return graph
