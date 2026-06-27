"""Standalone rubric evaluation for review outputs.

Decoupled from any specific agent class. Takes a review text + LLM + rubric standard,
returns a structured rating. Used as post-processing after any reviewer agent produces output.
"""

import json
import logging
import re

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

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


def _build_rubric_prompt(rubric: RubricStandard) -> str:
    criteria_block = "\n".join(
        f"- {c.name} (weight: {int(c.weight * 100)}%): {c.description}\n"
        f"  Anchors: {'; '.join(f'{k}: {v}' for k, v in c.anchors.items())}"
        for c in rubric.criteria
    )
    return f"""RUBRIC EVALUATION

You must evaluate this review using the "{rubric.name}" rubric standard ({rubric.publisher}).

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
- confidence: high = full review with clear evidence; medium = partial or ambiguous evidence; low = insufficient data
- If the review appears to cite specific code, architecture names, or references not grounded in the paper content, penalize Technical Soundness and note the hallucination risk in scoring_notes
"""


def _parse_rating_json(text: str) -> dict | None:
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


def _validate_rating(rating: dict, rubric: RubricStandard) -> dict:
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


def _build_messages(
    rubric: RubricStandard, review_text: str, system_prompt: str, extra_instructions: str = ""
) -> list:
    base_prompt = _build_rubric_prompt(rubric)
    if extra_instructions:
        base_prompt += f"\n\n{extra_instructions}"
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"{base_prompt}\n\nUse the following review to inform your evaluation:\n\n{review_text}"),
    ]


async def _try_structured_output(
    llm: BaseChatModel, rubric: RubricStandard, review_text: str, system_prompt: str
) -> dict | None:
    try:
        structured_llm = llm.with_structured_output(RubricRatingModel)
        messages = _build_messages(rubric, review_text, system_prompt)
        result = await structured_llm.ainvoke(messages)
        if isinstance(result, RubricRatingModel):
            return result.model_dump()
        return None
    except Exception as e:
        logger.debug(f"Structured output not supported or failed: {e}")
        return None


async def _try_json_retry(
    llm: BaseChatModel, rubric: RubricStandard, review_text: str, system_prompt: str, max_retries: int = 3
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
        messages = _build_messages(rubric, review_text, system_prompt, retry_prompts[attempt])
        response = await llm.ainvoke(messages)
        content = response.content if isinstance(response.content, str) else str(response.content)
        rating = _parse_rating_json(content)
        if rating:
            return rating
        logger.warning(f"Rubric JSON parse failed on attempt {attempt + 1}/{max_retries}")
    return None


async def evaluate_rubric(
    llm: BaseChatModel,
    review_text: str,
    rubric_standard: str = "general",
    system_prompt: str = "You are an expert academic reviewer.",
) -> dict:
    """Evaluate a review output against a rubric standard.

    Args:
        llm: The LLM to use for evaluation.
        review_text: The review content to evaluate.
        rubric_standard: Rubric ID (e.g. "general", "ieee", "acm").
        system_prompt: System prompt for the evaluation LLM call.

    Returns:
        dict with overall_score, confidence, criteria, scoring_notes.
    """
    rubric = get_rubric_standard(rubric_standard)

    structured = await _try_structured_output(llm, rubric, review_text, system_prompt)
    if structured:
        logger.info("Rubric evaluation succeeded via structured output")
        return _validate_rating(structured, rubric)

    logger.info("Structured output unavailable, falling back to JSON retry")
    fallback = await _try_json_retry(llm, rubric, review_text, system_prompt)
    if fallback:
        return _validate_rating(fallback, rubric)

    return {
        "overall_score": 0,
        "confidence": "low",
        "rubric_standard": rubric.name,
        "criteria": [],
        "scoring_notes": "Rating extraction failed after all attempts",
    }
