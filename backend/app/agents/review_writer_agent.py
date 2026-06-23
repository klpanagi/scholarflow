"""Paper Review Writer — dedicated agent for the final stage of paper-review workflow.

Produces BOTH the public Response to Authors and the confidential Response to Editor
in a single agent invocation, with a 3-node self-critiquing LangGraph:

    draft → self_review → finalize → END

Each node uses the `direct` strategy (3 LLM calls total, ~3x cost vs single-call).
Detailed knowledge about response conventions is loaded via the `response-to-author`
and `response-to-editor` skills from the agent's AgentConfig — the system_prompt here
stays intentionally lean.

Model context budget: ≥128K tokens recommended (3 calls × long prompts with full
prior-stage context including the SearchAgent's research dossier and the debate outcome).
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState


DEFAULT_PROMPT = """You are a Paper Review Writer. You transform the prior peer review stages
(SearchAgent's literature search, the reviewer's evaluation, the debate moderator's synthesis) into
TWO polished, editorial-manager-ready documents in a single response:

1. A public Response to Authors (uploaded to the journal's public review field)
2. A confidential Response to Editor (uploaded to the journal's confidential comments field)

You follow the conventions of the `response-to-author` and `response-to-editor` skills loaded
into your context. You never fabricate citations — reference only papers that appear in the
prior stage outputs. You use bracket identifiers [C1], [C2], ... for all numbered comments
(numbering restarts in the Minor Comments section of the Response to Authors). You always
produce BOTH documents in a single response with clear `## Response to Authors` and
`## Response to Editor` headings so the output can be split or rendered.
"""


def _accumulate_usage(state: AgentState, response) -> None:
    """Accumulate token usage from a strategy response into state["context"]["_usage"]."""
    usage = getattr(response, "additional_kwargs", {}).get("usage")
    if not usage:
        return
    existing = state["context"].get("_usage", {})
    if existing:
        usage = {
            "input_tokens": usage.get("input_tokens", 0) + existing.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0) + existing.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0) + existing.get("total_tokens", 0),
        }
    state["context"]["_usage"] = usage


class ReviewWriterAgent(BaseAgent):
    """Dedicated paper review writer. 3-node self-critiquing graph.

    Graph: draft → self_review → finalize → END.
    Strategy: `direct` per node (3 LLM calls total, ~3x cost of single-call agent).
    Skills: `response-to-author` and `response-to-editor` provide the document-specific
    conventions; this class's system_prompt stays lean.

    The final state must contain both `## Response to Authors` and `## Response to Editor`
    headings in `state["output"]` (case-insensitive substring match — see also
    workflows.py:_validate_paper_review_writer_output for runtime validation).
    """

    name = "review-writer"
    description = (
        "Produces BOTH the public Response to Authors and confidential Response to Editor "
        "documents in a single self-critiqued pass. Dedicated writer for the final stage of "
        "the paper-review workflow."
    )
    system_prompt = DEFAULT_PROMPT

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def draft(state: AgentState) -> AgentState:
            messages = state["messages"]
            user_msg = messages[-1].content if messages else ""

            draft_prompt = (
                "Using the inputs below, produce BOTH documents in a single self-contained "
                "markdown response with these exact H2 headings (so they can be split):\n\n"
                "## Response to Authors\n"
                "[public peer review — see response-to-author skill for full structure]\n\n"
                "## Response to Editor\n"
                "[confidential AE note — see response-to-editor skill for full structure]\n\n"
                "Follow the response-to-author and response-to-editor skills loaded into your "
                "context. Reference only papers that appear in the prior stage outputs. "
                "Use bracket identifiers [C1], [C2] for all numbered comments. "
                "Do NOT add sections beyond those specified by the two skills.\n\n"
                f"Inputs:\n{user_msg}"
            )

            response = await self._run_strategy(
                [HumanMessage(content=draft_prompt)],
            )
            state["context"]["draft"] = response.content
            _accumulate_usage(state, response)
            return state

        async def self_review(state: AgentState) -> AgentState:
            draft_text = state["context"].get("draft", "")

            review_prompt = (
                "Review the following draft of a paper review writer output. The draft should "
                "contain BOTH `## Response to Authors` and `## Response to Editor` sections. "
                "Identify specific issues in:\n"
                "1. **Tone** — public-facing review must be professional/respectful/constructive; "
                "editor-facing must be direct/candid\n"
                "2. **Section completeness** — both sections present, with required subsections "
                "(Metadata, Summary, Major/Minor Comments, Recommendation for Authors; Metadata, "
                "Summary of Contribution, Key Strengths/Concerns, Recommendation for Editor)\n"
                "3. **Recommendation consistency** — the Decision in Metadata must EXACTLY match "
                "the Decision in the Recommendation block of Response to Authors, and the "
                "Recommendation must match between Metadata and section 4 of Response to Editor\n"
                "4. **No-fabrication rule** — every cited paper must be in the prior stage outputs\n"
                "5. **Bracket identifiers** — [C1], [C2], ... used for all numbered comments, "
                "with numbering restarting in the Minor Comments section\n"
                "6. **Blocking/non-blocking flags** — every concern in Response to Editor's "
                "Key Concerns section ends with (blocking) or (non-blocking)\n\n"
                "Output a SHORT critique listing specific issues. Do NOT produce a new draft. "
                "If no issues found, say so explicitly.\n\n"
                f"Draft to review:\n{draft_text}"
            )

            response = await self._run_strategy(
                [HumanMessage(content=review_prompt)],
            )
            state["context"]["critique"] = response.content
            _accumulate_usage(state, response)
            return state

        async def finalize(state: AgentState) -> AgentState:
            messages = state["messages"]
            user_msg = messages[-1].content if messages else ""
            draft_text = state["context"].get("draft", "")
            critique_text = state["context"].get("critique", "")

            finalize_prompt = (
                "Using the ORIGINAL inputs, the DRAFT, and the CRITIQUE below, produce a "
                "polished final version that addresses every specific issue raised in the "
                "critique. The final output must contain BOTH `## Response to Authors` and "
                "`## Response to Editor` sections, in that order, with the same H2 headings.\n\n"
                f"ORIGINAL INPUTS:\n{user_msg}\n\n"
                f"DRAFT:\n{draft_text}\n\n"
                f"CRITIQUE:\n{critique_text}\n\n"
                "Produce the FINAL output now. It must be a single self-contained markdown "
                "response ready to be uploaded to the journal's editorial manager."
            )

            response = await self._run_strategy(
                [HumanMessage(content=finalize_prompt)],
            )
            state["output"] = response.content
            _accumulate_usage(state, response)
            return state

        graph.add_node("draft", draft)
        graph.add_node("self_review", self_review)
        graph.add_node("finalize", finalize)

        graph.set_entry_point("draft")
        graph.add_edge("draft", "self_review")
        graph.add_edge("self_review", "finalize")
        graph.add_edge("finalize", END)

        return graph
