"""Workflow-integrated paper review agent.

Consumes research_dossier from SearchAgent stage as an evidence corpus.
Config-driven: system_prompt + skills determine review methodology.
Replaces the lightweight standalone PaperReviewAgent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState

if TYPE_CHECKING:
    from app.agents.dossier import ResearchDossier


DEFAULT_REVIEW_PROMPT = """You are an expert academic reviewer. You evaluate documents rigorously, providing structured, evidence-based reviews.

Your review must include:
- **Summary**: Brief overview of the document's contribution
- **Strengths**: Key positive aspects (3-5 points)
- **Weaknesses**: Key concerns (3-5 points)
- **Detailed Assessment**: Section-by-section analysis
- **Recommendations**: Specific actionable improvements
- **Decision**: Accept / Minor Revision / Major Revision / Reject

Be constructive, specific, and fair. Always cite evidence from the document to support your assessments.
"""


def _format_dossier_context(dossier: ResearchDossier) -> str:
    """Format a ResearchDossier into a prompt section for the analyze node."""
    sections: list[str] = []

    sections.append("Top related papers:")
    if dossier.papers:
        for i, p in enumerate(dossier.papers[:10], 1):
            year = str(p.year) if p.year is not None else "n/a"
            citations = str(p.citation_count) if p.citation_count is not None else "0"
            sections.append(f"{i}. {p.title} ({year}, {citations} citations)")
    else:
        sections.append("0 related papers found.")

    sections.append("")
    sections.append("Identified research gaps:")
    if dossier.gaps:
        for g in dossier.gaps[:5]:
            sections.append(f"- {g.concept_a} + {g.concept_b}: {g.description}")
    else:
        sections.append("- No research gaps identified.")

    sections.append("")
    sections.append("Methodology landscape:")
    if dossier.methodologies:
        sections.append("| Method | Dataset | Metrics | Result |")
        sections.append("| --- | --- | --- | --- |")
        for m in dossier.methodologies[:10]:
            metrics_str = ", ".join(m.metrics) if m.metrics else "n/a"
            sections.append(f"| {m.method_name} | {m.dataset} | {metrics_str} | {m.result} |")
    else:
        sections.append("| No methodology entries found. |")

    return "## Available Evidence Corpus (from Scholar Agent)\n\n" + "\n".join(sections)


class PaperReviewAgent(BaseAgent):
    """Workflow-integrated paper review agent.

    Consumes Scholar Agent's research_dossier as evidence corpus when available.
    The system_prompt (from AgentConfig) drives the review focus and methodology.
    The skills (from AgentConfig) provide domain-specific knowledge.

    Graph: analyze → respond → END (2 LLM calls by default).
    Strategy-aware: uses critique/reflection/direct strategies as configured.
    """

    name = "paper-review"
    description = "Workflow-integrated paper review. Consumes Scholar Agent's research_dossier as evidence corpus."
    system_prompt = DEFAULT_REVIEW_PROMPT

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def analyze(state: AgentState) -> AgentState:
            messages = state["messages"]
            user_msg = messages[-1].content if messages else ""

            content_preview = user_msg[:10000]

            dossier = state["context"].get("research_dossier")
            dossier_context = ""
            if dossier is not None:
                dossier_context = _format_dossier_context(dossier) + "\n\n"

            analysis_prompt = (
                f"{dossier_context}"
                "Analyze this document and identify:\n"
                "1. Core contribution and significance\n"
                "2. Key methodology or approach\n"
                "3. Strengths and potential weaknesses\n"
                "4. Section structure and content quality\n"
                "5. Any specific concerns or red flags\n\n"
                f"Document content:\n{content_preview}"
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
                "Now produce a complete, structured review following this format:\n\n"
                "## Summary\n[Brief overview of the document and its contribution]\n\n"
                "## Strengths\n[3-5 numbered points with evidence]\n\n"
                "## Weaknesses\n[3-5 numbered points with evidence]\n\n"
                "## Detailed Assessment\n[Section-by-section analysis covering methodology, "
                "novelty/significance, clarity, and reproducibility/completeness]\n\n"
                "## Recommendations for Authors\n[Specific, actionable improvement suggestions]\n\n"
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
