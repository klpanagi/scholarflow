"""Workflow-integrated paper review agent.

Consumes research_dossier from SearchAgent stage as an evidence corpus.
Config-driven: system_prompt + skills determine review methodology.
Replaces the lightweight standalone variant.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState
from app.utils.context_budget import budget_for_stages, fit_to_budget

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

    return "## Available Evidence Corpus (from Search Agent)\n\n" + "\n".join(sections)


class ReviewAgent(BaseAgent):
    """Workflow-integrated paper review agent.

    Consumes Search Agent's research_dossier as evidence corpus when available.
    The system_prompt (from AgentConfig) drives the review focus and methodology.
    The skills (from AgentConfig) provide domain-specific knowledge.

    Graph: analyze → respond → END (2 LLM calls by default).
    Strategy-aware: uses critique/reflection/direct strategies as configured.
    """

    name = "review"
    description = "Workflow-integrated paper review. Consumes Search Agent's research_dossier as evidence corpus."
    system_prompt = DEFAULT_REVIEW_PROMPT

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def analyze(state: AgentState) -> AgentState:
            messages = state["messages"]
            user_msg = messages[-1].content if messages else ""

            # Use full paper_content from context if available (extracted from chunks),
            # otherwise fall back to the message content. Apply budget-aware truncation
            # instead of a hard character cap.
            paper_content = state["context"].get("paper_content", "")
            print(
                f"[ReviewAgent] paper_content length={len(paper_content) if paper_content else 0} chars, "
                f"user_msg length={len(user_msg) if user_msg else 0} chars",
                flush=True,
            )
            content = paper_content if paper_content else user_msg

            model_name = getattr(self.llm, "model_name", None)
            output_tokens = getattr(self.llm, "max_tokens", 4096)
            budgets = budget_for_stages(model=model_name, output_tokens=output_tokens)
            content_preview = fit_to_budget(content, budgets["paper_content"], label="review")
            print(
                f"[ReviewAgent] content_preview length={len(content_preview)} chars, "
                f"budget={budgets['paper_content']} tokens",
                flush=True,
            )

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

            response = await self._run_strategy(
                messages[:-1] + [HumanMessage(content=analysis_prompt)],
            )
            state["context"]["analysis"] = response.content
            usage = getattr(response, "additional_kwargs", {}).get("usage")
            if usage:
                state["context"]["_usage"] = usage

            return state

        async def respond(state: AgentState) -> AgentState:
            analysis = state["context"].get("analysis", "")

            # Build a clean message list: keep only system messages from the
            # original conversation.  The original HumanMessage carries only
            # metadata (title, authors, abstract) because the workflow uses
            # has_separate_paper_content=True — the full paper was processed by
            # the analyze node and is available in `analysis`.  Including the
            # metadata-only HumanMessage causes the LLM to believe it received
            # insufficient input and produce a crippled review.
            from langchain_core.messages import BaseMessage, SystemMessage

            original_messages = state["messages"]
            system_messages: list[BaseMessage] = [
                m for m in original_messages if isinstance(m, SystemMessage)
            ]

            review_prompt = (
                f"Based on the following comprehensive analysis of the paper:\n\n{analysis}\n\n"
                "Now produce a complete, structured review following this format:\n\n"
                "## Summary\n[Brief overview of the document and its contribution]\n\n"
                "## Strengths\n[3-5 numbered points with evidence]\n\n"
                "## Weaknesses\n[3-5 numbered points with evidence]\n\n"
                "## Detailed Assessment\n[Section-by-section analysis covering methodology, "
                "novelty/significance, clarity, and reproducibility/completeness]\n\n"
                "## Recommendations for Authors\n[Specific, actionable improvement suggestions]\n\n"
                "## Decision\n[Accept / Minor Revision / Major Revision / Reject with justification]\n\n"
                "RULES:\n"
                "- You have been provided with the full paper content and a detailed analysis.\n"
                "- Do NOT write that you lack access to the paper or that your review is based on a secondary summary.\n"
                "- Do NOT cite specific code, architecture names, class names, table/figure/section numbers,\n"
                "  or reference-list entries that are not present in the provided text.\n"
                "- If a criterion cannot be assessed from the available content, note the specific limitation\n"
                "  (e.g., 'no experimental results section is present') rather than hedging about access.\n"
                "- Separate observation from inference. Use hedging for inferences, not for access disclaimers."
            )

            response = await self._run_strategy(
                system_messages + [HumanMessage(content=review_prompt)],
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
