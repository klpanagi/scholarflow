import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent, AgentState
from app.utils.context_budget import fit_to_budget, budget_for_stages
from app.utils.pdf_model_support import model_supports_pdf, create_multimodal_human_message
from app.services.pdf_service import pdf_service
from app.services.rubric_standards import get_rubric_standard, RubricStandard

logger = logging.getLogger(__name__)

class RubricCriterionScore(BaseModel):
    name: str = Field(description="Criterion name exactly as defined in the rubric")
    score: int = Field(ge=1, le=100, description="Score from 1 to 100")
    justification: str = Field(description="1-2 sentence justification for this score")


class RubricRatingModel(BaseModel):
    overall_score: int = Field(ge=1, le=100, description="Weighted average score 1-100")
    confidence: str = Field(description="high, medium, or low")
    confidence_reason: str = Field(description="Brief explanation of confidence level")
    criteria: list[RubricCriterionScore] = Field(description="Per-criterion scores")
    scoring_notes: str = Field(description="1-2 sentence overall assessment summary")


DEEP_REVIEW_SYSTEM_PROMPT = """You are a rigorous document reviewer specializing in academic and professional content. You follow a structured 7-stage pipeline to produce comprehensive, evidence-based reviews of papers, grants, proposals, deliverables, and other formal documents.

Produce a single consolidated review that is thorough, evidence-based, and constructive. Never be dismissive. Adapt your evaluation criteria to the document type:
- Papers: novelty, methodology, validity, reproducibility, clarity
- Grants/Proposals: feasibility, impact, methodology, budget justification, innovation
- Deliverables: completeness, quality, alignment with requirements, actionable insights
"""


class DeepReviewAgent(BaseAgent):
    name = "deep-reviewer"
    description = "7-stage deep review pipeline (intake→structural→claims→literature→methodology→adversarial→synthesis). Heavy: 8-10 LLM calls, 130-150K tokens. Config-driven via system_prompt and skills."
    system_prompt = DEEP_REVIEW_SYSTEM_PROMPT

    def _get_tool(self, name: str):
        for t in self.tools:
            if getattr(t, "name", None) == name:
                return t
        return None

    def _get_model_name(self) -> str:
        if hasattr(self.llm, "model_name"):
            return self.llm.model_name
        if hasattr(self.llm, "model"):
            return self.llm.model
        return ""

    async def _invoke_with_usage(
        self, state: AgentState | None, messages: list, accumulate: bool = True
    ) -> AIMessage:
        response = await self.llm.ainvoke(messages)
        if accumulate and state is not None:
            um = getattr(response, "usage_metadata", None) or {}
            usage = {
                "input_tokens": um.get("input_tokens", 0) or 0,
                "output_tokens": um.get("output_tokens", 0) or 0,
                "total_tokens": um.get("total_tokens", 0) or 0,
            }
            existing = state["context"].get("_usage", {})
            state["context"]["_usage"] = {
                "input_tokens": existing.get("input_tokens", 0) + usage["input_tokens"],
                "output_tokens": existing.get("output_tokens", 0) + usage["output_tokens"],
                "total_tokens": existing.get("total_tokens", 0) + usage["total_tokens"],
            }
        return response

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        graph.add_node("intake", self._intake)
        graph.add_node("structural", self._structural_analysis)
        graph.add_node("claims", self._claim_extraction)
        graph.add_node("methodology", self._methodology_verification)
        graph.add_node("literature", self._literature_grounding)
        graph.add_node("adversarial", self._adversarial_red_team)
        graph.add_node("synthesis", self._synthesis)

        graph.set_entry_point("intake")
        graph.add_edge("intake", "structural")
        graph.add_edge("structural", "claims")
        graph.add_edge("claims", "methodology")
        graph.add_edge("methodology", "literature")
        graph.add_edge("literature", "adversarial")
        graph.add_edge("adversarial", "synthesis")
        graph.add_edge("synthesis", END)

        return graph

    async def _intake(self, state: AgentState) -> AgentState:
        paper_content = state["context"].get("paper_content", "")

        if not paper_content:
            for msg in state["messages"]:
                if isinstance(msg, HumanMessage):
                    if isinstance(msg.content, list):
                        for part in msg.content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text = part["text"]
                                if text.startswith("You are a Paper Reviewer"):
                                    marker = "Paper:\n"
                                    idx = text.find(marker)
                                    if idx != -1:
                                        paper_content = text[idx + len(marker):]
                                        break
                                elif text.strip():
                                    paper_content = text
                                    break
                    elif isinstance(msg.content, str):
                        text = msg.content
                        if text.startswith("You are a Paper Reviewer"):
                            marker = "Paper:\n"
                            idx = text.find(marker)
                            if idx != -1:
                                paper_content = text[idx + len(marker):]
                                break
                        elif text.strip():
                            paper_content = text
                            break
                    if paper_content:
                        break

        if not paper_content:
            file_key = state["context"].get("file_key")
            if file_key:
                from app.services.minio_service import minio_service
                paper_content_bytes = await minio_service.download_file(file_key)
                paper_content = paper_content_bytes.decode("utf-8", errors="replace")

        state["context"]["paper_content"] = paper_content

        model_name = getattr(self.llm, "model_name", None)
        output_tokens = getattr(self.llm, "max_tokens", 4096)
        budgets = budget_for_stages(model=model_name, output_tokens=output_tokens)
        paper_fitted = fit_to_budget(paper_content, budgets["paper_content"], label="intake")

        pdf_bytes = state["context"].get("pdf_bytes")

        # D-1: single-intake GROBID extraction → state["context"]["grobid"] for downstream stages.
        if pdf_bytes and "grobid" not in state["context"]:
            try:
                grobid_result = await pdf_service.grobid_extract(pdf_bytes)
                state["context"].setdefault("grobid", grobid_result.to_dict())
                logger.info(
                    "GROBID extraction complete: source=%s title=%r refs=%d time=%.2fs",
                    grobid_result.source,
                    grobid_result.title,
                    len(grobid_result.references),
                    grobid_result.extraction_time,
                )
            except Exception as exc:
                # Fallback: empty dict keeps downstream shape consistent.
                logger.warning(
                    "GROBID extraction failed, continuing without structured bibliography: %s",
                    exc,
                )
                state["context"].setdefault("grobid", {})
        elif not pdf_bytes:
            logger.info("No pdf_bytes in context, skipping GROBID extraction")
            state["context"].setdefault("grobid", {})

        model_name = self._get_model_name()
        use_pdf = pdf_bytes and model_supports_pdf(model_name)

        intake_prompt = f"""Stage 0: INTAKE

Extract structured data: title, authors/creators, abstract/executive summary, document type, key sections, and domain.

Document content:
{paper_fitted}"""

        if use_pdf:
            messages = [
                SystemMessage(content=self.system_prompt),
                create_multimodal_human_message(pdf_bytes, intake_prompt),
            ]
        else:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=intake_prompt),
            ]

        response = await self._invoke_with_usage(state, messages)
        state["context"]["intake"] = response.content
        return state

    async def _structural_analysis(self, state: AgentState) -> AgentState:
        intake = state["context"].get("intake", "")
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Stage 1: STRUCTURAL ANALYSIS

Evaluate IMRaD completeness, figure/table quality, references, writing quality. Score 1-10.

{intake}"""),
        ]

        response = await self._invoke_with_usage(state, messages)
        state["context"]["structural"] = response.content
        return state

    async def _claim_extraction(self, state: AgentState) -> AgentState:
        intake = state["context"].get("intake", "")
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Stage 2: CLAIM EXTRACTION

List the top 5 claims and their evidence strength (Strong/Moderate/Weak/Unsupported).

{intake}"""),
        ]

        response = await self._invoke_with_usage(state, messages)
        state["context"]["claims"] = response.content
        return state

    async def _literature_grounding(self, state: AgentState) -> AgentState:
        claims = state["context"].get("claims", "")
        intake = state["context"].get("intake", "")

        # Consume GROBID bibliography injected by _intake() for structured reference coverage.
        # References extracted by GROBID are available in `state.context.grobid.references`.
        grobid = state["context"].get("grobid") or {}
        grobid_references = grobid.get("references", [])

        scholar_output = ""
        for msg in state.get("messages", []):
            text = msg.content if hasattr(msg, "content") else ""
            if "--- PRIOR STAGE OUTPUTS ---" in text:
                idx = text.find("--- PRIOR STAGE OUTPUTS ---")
                scholar_output = text[idx:idx + 4000]
                break

        grobid_refs_block = ""
        if grobid_references:
            ref_lines = []
            for i, ref in enumerate(grobid_references[:30], start=1):
                title = (ref.get("title") or ref.get("raw_text") or "")[:120].strip()
                year = ref.get("year") or "n.d."
                doi = ref.get("doi") or ""
                ref_lines.append(f"[{i}] {title} ({year}) {doi}".rstrip())
            grobid_refs_block = (
                f"\n\nStructured References (GROBID extraction, "
                f"{len(grobid_references)} total):\n"
                + "\n".join(ref_lines)
            )

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Stage 3: LITERATURE GROUNDING

Assess literature coverage, baselines, novelty. Are key citations missing?
Use the Scholar Agent's search results below to evaluate related work coverage.
References extracted by GROBID are available in `state.context.grobid.references`.

Claims: {claims}
{grobid_refs_block}

Scholar Output (from prior stage):
{scholar_output[:3000]}"""),
        ]

        response = await self._invoke_with_usage(state, messages)
        state["context"]["literature"] = response.content
        return state

    async def _methodology_verification(self, state: AgentState) -> AgentState:
        intake = state["context"].get("intake", "")
        claims = state["context"].get("claims", "")

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Stage 4: METHODOLOGY VERIFICATION

Evaluate statistical rigor, reproducibility, experimental design, threats to validity.

Intake: {intake}
Claims: {claims}"""),
        ]

        response = await self._invoke_with_usage(state, messages)
        state["context"]["methodology"] = response.content
        return state

    async def _adversarial_red_team(self, state: AgentState) -> AgentState:
        claims = state["context"].get("claims", "")
        methodology = state["context"].get("methodology", "")

        # Consume GROBID references + sections for citation plausibility and source criticism.
        grobid = state["context"].get("grobid") or {}
        grobid_references = grobid.get("references", [])
        grobid_sections = grobid.get("sections", [])

        grobid_audit_block = ""
        if grobid_references or grobid_sections:
            grobid_audit_block = (
                f"\n\n## GROBID Citation/Source Audit\n"
                f"{len(grobid_references)} references (state.context.grobid.references) "
                f"and {len(grobid_sections)} sections (state.context.grobid.sections) "
                f"were extracted from the PDF. Challenge suspicious citations: missing DOIs, "
                f"implausible years, venues outside the field, broken author lists, and "
                f"structural gaps where key sections are absent or thin."
            )

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Stage 5: ADVERSARIAL RED TEAM

Breaker: logical flaws. Butcher: missing experiments. Collector: novelty threats.

Claims: {claims}
Methodology: {methodology}
{grobid_audit_block}"""),
        ]

        response = await self._invoke_with_usage(state, messages)
        state["context"]["adversarial"] = response.content
        return state

    def _build_rubric_prompt(self, rubric: RubricStandard) -> str:
        criteria_block = "\n".join(
            f"- {c.name} (weight: {int(c.weight * 100)}%): {c.description}\n"
            f"  Anchors: {'; '.join(f'{k}: {v}' for k, v in c.anchors.items())}"
            for c in rubric.criteria
        )
        return f"""RUBRIC EVALUATION

You must evaluate this manuscript using the "{rubric.name}" rubric standard ({rubric.publisher}).

Rate each criterion on a scale of 1-100, then compute the weighted overall score.

Criteria:
{criteria_block}

OUTPUT FORMAT — You MUST respond with a single JSON code block. No text before or after.

```json
{{
  "overall_score": <weighted average 1-100>,
  "confidence": "<high|medium|low>",
  "confidence_reason": "<brief explanation of confidence level>",
  "criteria": [
    {{"name": "<criterion name>", "score": <1-100>, "justification": "<1-2 sentence justification>"}},
    ...
  ],
  "scoring_notes": "<1-2 sentence summary of the overall assessment>"
}}
```

Scoring rules:
- overall_score MUST be the weighted average: sum(criterion.score * criterion.weight) rounded to nearest integer
- Each criterion score must be 1-100
- Use the anchors above as calibration guides
- confidence: high = full document text available + clear evidence; medium = review covers only some criteria or contradicts itself; low = missing content or mostly fabricated details
- NOTE: Appropriate academic hedging language (e.g., "appears to", "suggests", "based on the text") is standard scholarly practice and does NOT reduce confidence. Only penalize confidence when the review is structurally incomplete or factually unsupported.
- If the review cites specific code, architecture names, or references not grounded in the provided analyses, penalize Technical Soundness and note the hallucination risk in scoring_notes
"""

    def _parse_rating_json(self, text: str) -> dict | None:
        match = re.search(r"```json\s*\n(.*?)\n\s*```", text, re.DOTALL)
        if not match:
            match = re.search(r"\{[^{}]*\"overall_score\"[^{}]*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            raw = match.group(1) if match.lastindex else match.group(0)
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _validate_rating(self, rating: dict, rubric: RubricStandard) -> dict:
        criteria = rating.get("criteria", [])
        if not criteria or len(criteria) != len(rubric.criteria):
            return rating

        computed_total = 0.0
        for rc in rubric.criteria:
            matched = next((c for c in criteria if c.get("name") == rc.name), None)
            if matched:
                score = max(1, min(100, int(matched.get("score", 50))))
                matched["score"] = score
                matched["weight"] = rc.weight
                computed_total += score * rc.weight

        rating["overall_score"] = max(1, min(100, round(computed_total)))
        return rating

    def _build_rubric_messages(
        self, rubric: RubricStandard, analyses: str, extra_instructions: str = ""
    ) -> list:
        base_prompt = self._build_rubric_prompt(rubric)
        if extra_instructions:
            base_prompt += f"\n\n{extra_instructions}"
        return [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"{base_prompt}\n\nUse the following analyses to inform your evaluation:\n\n{analyses}"),
        ]

    async def _try_structured_output(
        self, rubric: RubricStandard, analyses: str
    ) -> dict | None:
        try:
            structured_llm = self.llm.with_structured_output(RubricRatingModel)
            messages = self._build_rubric_messages(rubric, analyses)
            result = await structured_llm.ainvoke(messages)
            if isinstance(result, RubricRatingModel):
                return result.model_dump()
            return None
        except Exception as e:
            logger.debug(f"Structured output not supported or failed: {e}")
            return None

    async def _try_json_retry(
        self, rubric: RubricStandard, analyses: str, max_retries: int = 3
    ) -> dict | None:
        retry_prompts = [
            "",
            "\n\nCRITICAL: Your previous response was NOT valid JSON. "
            "You MUST respond with ONLY a JSON code block. No markdown, no explanation, no text outside the code block. "
            "Start your response with ```json and end with ```.",
            "\n\nSTRICT REQUIREMENT: You MUST output ONLY a JSON object inside a ```json code block. "
            "Any text outside the JSON block will be rejected. "
            "Do NOT write 'Here is the JSON' or any preamble. Start directly with ```json.",
        ]
        for attempt in range(max_retries):
            messages = self._build_rubric_messages(rubric, analyses, retry_prompts[attempt])
            response = await self._invoke_with_usage(None, messages, accumulate=False)
            content = response.content if isinstance(response.content, str) else str(response.content)
            rating = self._parse_rating_json(content)
            if rating:
                return rating
            logger.warning(f"Rubric JSON parse failed on attempt {attempt + 1}/{max_retries}")
        return None

    async def _invoke_rubric_evaluation(
        self, state: AgentState, rubric: RubricStandard, analyses: str
    ) -> dict:
        structured = await self._try_structured_output(rubric, analyses)
        if structured:
            logger.info("Rubric evaluation succeeded via structured output")
            return self._validate_rating(structured, rubric)

        logger.info("Structured output unavailable, falling back to JSON retry")
        fallback = await self._try_json_retry(rubric, analyses)
        if fallback:
            return self._validate_rating(fallback, rubric)

        return {
            "overall_score": 0,
            "confidence": "low",
            "rubric_standard": rubric.name,
            "criteria": [],
            "scoring_notes": "Rating extraction failed after all attempts",
        }

    async def _synthesis(self, state: AgentState) -> AgentState:
        intake = state["context"].get("intake", "")
        structural = state["context"].get("structural", "")
        claims = state["context"].get("claims", "")
        literature = state["context"].get("literature", "")
        methodology = state["context"].get("methodology", "")
        adversarial = state["context"].get("adversarial", "")

        rubric_id = state["context"].get("rubric_standard", "general")
        rubric = get_rubric_standard(rubric_id)

        analyses = f"""Intake: {intake}

Structural Analysis: {structural}

Claim Extraction: {claims}

Literature Grounding: {literature}

Methodology Verification: {methodology}

Adversarial Red Team: {adversarial}"""

        review_prompt = f"""SYNTHESIS — REVIEW DOCUMENT

Using the analyses below, produce a single consolidated review in professional academic markdown.

Use the following EXACT sections:

## Executive Summary
A 2-3 sentence overview of the document and the review verdict.

## Strengths
Numbered list of the document's key strengths with evidence from the analyses.

## Weaknesses
Numbered list of the document's key weaknesses with evidence from the analyses.

## Detailed Analysis
Subsections covering: Technical Soundness, Originality/Innovation, Significance/Impact, Clarity, Literature Grounding, Reproducibility/Feasibility. Each subsection should reference specific findings from the prior stages.

## Recommendations
Actionable, numbered improvement suggestions.

## Verdict
One of: Accept, Minor Revision, Major Revision, Reject. Include a 1-2 sentence justification.

Do NOT include any JSON or score tables in this output. Focus on the qualitative review text.

CRITICAL RULES:
- Base your review ONLY on the analyses provided below. Do not introduce new information.
- Do NOT cite specific code, architecture names, class names, table/figure/section numbers,
  or reference-list entries that are not present in the analyses.
- If an analysis is incomplete or missing, note the limitation. Do NOT fabricate details.
- Separate observation from inference. Use hedging language for inferences.

Analyses:
{analyses}"""

        pdf_bytes = state["context"].get("pdf_bytes")
        model_name = self._get_model_name()
        use_pdf = pdf_bytes and model_supports_pdf(model_name)

        if use_pdf:
            review_messages = [
                SystemMessage(content=self.system_prompt),
                create_multimodal_human_message(pdf_bytes, review_prompt),
            ]
        else:
            review_messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=review_prompt),
            ]

        review_response = await self._invoke_with_usage(state, review_messages)
        state["output"] = review_response.content

        rating = await self._invoke_rubric_evaluation(state, rubric, analyses)
        rating["rubric_standard"] = rubric.name
        state["context"]["rating"] = rating

        state["metadata"]["usage"] = state["context"].get("_usage", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
        state["metadata"]["stages_completed"] = [
            "intake", "structural", "claims", "literature",
            "methodology", "adversarial", "synthesis",
        ]
        return state
