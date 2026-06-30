import json
import logging

from langchain_core.messages import HumanMessage

from app.services.llm_service import llm_service
from app.schemas.paper_analysis import PaperAnalysis
from app.utils.context_budget import get_context_budget, fit_to_budget

logger = logging.getLogger(__name__)

DEFAULT_LLM_MODEL = "google/gemma-4-31b-it:free"
DEFAULT_LLM_PROVIDER = "openrouter"


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response, handling markdown fences and trailing content."""
    import re

    # Strip markdown code fences first
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    for open_char, close_char in [("{", "}"), ("[", "]")]:
        start = text.find(open_char)
        end = text.rfind(close_char)
        if start != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                # Try closing truncated JSON by appending missing brackets
                snippet = text[start:]
                depth = 0
                for ch in snippet:
                    if ch == open_char:
                        depth += 1
                    elif ch == close_char:
                        depth -= 1
                fix = snippet + close_char * max(depth, 0)
                try:
                    json.loads(fix)
                    return fix
                except json.JSONDecodeError:
                    continue
    return text


async def _invoke_llm(
    prompt: str,
    model: str = DEFAULT_LLM_MODEL,
    provider: str = DEFAULT_LLM_PROVIDER,
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> str:
    logger.info(f"Invoking LLM: provider={provider}, model={model}")
    llm = llm_service.get_llm(
        model=model,
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    content = response.content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        content = "".join(text_parts)
    logger.info(f"LLM response length: {len(content) if content else 0} chars")
    return content


ANALYSIS_PROMPT = """Analyze this academic document and produce a structured assessment.

Title: {title}
Abstract: {abstract}
Document Type: {doc_type}

Content (excerpt):
{content}

Respond in EXACTLY this JSON format. Every field is REQUIRED.

{{
  "summary": "2-4 sentence overview of the paper's main contribution and approach",
  "key_findings": ["finding 1", "finding 2", "finding 3"],
  "methodology": "description of methods, techniques, or approaches used",
  "contributions": ["contribution 1", "contribution 2"],
  "limitations": ["limitation 1", "limitation 2"],

  "strengths": [
    {{"point": "strength description", "evidence": "supporting quote or fact from the text", "severity": "major"}}
  ],
  "weaknesses": [
    {{"point": "weakness description", "evidence": "supporting quote or fact from the text", "severity": "major"}}
  ],
  "suggestions": ["specific improvement suggestion 1", "suggestion 2"],

  "scientific_areas": ["primary field", "secondary field"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "field_of_study": "Computer Science",
  "subfield": "specific subfield",

  "quality_score": 7.5,
  "quality_rationale": "explanation of quality score",
  "novelty_score": 7.0,
  "novelty_rationale": "explanation of novelty score",
  "rigor_score": 7.0,
  "rigor_rationale": "explanation of rigor score",
  "clarity_score": 7.5,
  "clarity_rationale": "explanation of clarity score",

  "doc_type": "journal",
  "venue_type": "journal",
  "estimated_venue_tier": "mid"
}}

SCORING RUBRIC (1-10):
- quality_score: Overall technical quality and soundness
- novelty_score: Originality of contribution relative to existing work
- rigor_score: Methodological rigor, experimental design, reproducibility
- clarity_score: Writing quality, structure, figure quality, readability

doc_type: journal | conference | preprint | thesis | report | other
venue_type: journal | conference | workshop | arxiv | other
estimated_venue_tier: top | high | mid | low | unknown

severity: critical | major | minor

RULES:
- Every field must be present. No nulls, no empty arrays where min_length > 0.
- Scores must be between 1.0 and 10.0.
- Provide exactly 1-5 strengths and 1-5 weaknesses.
- Keywords must be lowercase, specific (not generic like "research" or "analysis").
- Return ONLY the JSON object. No markdown fences, no explanation."""


async def analyze_paper(
    title: str,
    abstract: str | None,
    full_text: str,
    doc_type: str = "other",
    model: str = DEFAULT_LLM_MODEL,
    provider: str = DEFAULT_LLM_PROVIDER,
) -> PaperAnalysis | None:
    budget = get_context_budget(model, output_tokens=4000)
    prompt_reserve = 2000
    content_budget = max(budget - prompt_reserve, 2000)
    content = fit_to_budget(full_text or "", content_budget, label="analysis")

    prompt = ANALYSIS_PROMPT.format(
        title=title or "Unknown",
        abstract=abstract or "Not available",
        doc_type=doc_type,
        content=content,
    )

    response_text = ""
    try:
        response_text = await _invoke_llm(
            prompt, model=model, provider=provider, temperature=0.3, max_tokens=8000,
        )
        if not response_text or not response_text.strip():
            raise ValueError("LLM returned empty response")
        raw = json.loads(_extract_json(response_text))

        raw.setdefault("doc_type", doc_type)
        raw.setdefault("venue_type", "other")
        raw.setdefault("estimated_venue_tier", "unknown")

        analysis = PaperAnalysis(**raw)
        return analysis

    except Exception as e:
        logger.error(f"Paper analysis failed for '{title}': {type(e).__name__}: {e}")
        if response_text:
            logger.error(f"Raw LLM response (first 500 chars): {response_text[:500]!r}")
        return None
