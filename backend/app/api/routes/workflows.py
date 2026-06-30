import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from langchain_core.messages import HumanMessage
import io

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user
from app.core.arq import get_arq_pool
from app.tasks.cancel import set_cancel
from app.api.deps import get_current_user_from_query
from app.models import AgentConfig, Paper, PaperChunk, AgentRole, WorkflowExecution, RevisionSession, RevisionMessage, agent_skills_table
from app.agents.factory import create_agent
from app.utils.context_budget import fit_to_budget, budget_for_stages
from app.utils.pdf_model_support import model_supports_pdf, create_multimodal_human_message
from app.services.llm_service import fetch_model_pricing, calculate_cost, llm_service
from app.services.pdf_service import pdf_service
from app.services.progress import (
    EventType,
    ExecutionEvent,
    ProgressManager,
    get_progress_manager,
)
from app.services.rubric_evaluation import evaluate_rubric
from app.schemas import (
    ExecutionEvent as ExecutionEventSchema,
    WorkflowExecutionResponse,
    WorkflowExecutionSnapshotResponse,
)

STAGE_TIMEOUT_SECONDS = 1800.0  # 30 minutes per stage
STAGE_DELAY_SECONDS = 15
HEARTBEAT_INTERVAL_SECONDS = 15.0  # SSE keep-alive cadence

TERMINAL_EXECUTION_STATUSES = frozenset(
    {"completed", "failed", "cancelled", "error", "partial", "cancelling"}
)


logger = logging.getLogger(__name__)


@dataclass
class PaperContent:
    text: str
    pdf_bytes: Optional[bytes] = None

router = APIRouter()


WORKFLOW_DEFINITIONS = {
    "paper-review": {
        "name": "Paper Review Pipeline",
        "stages": [
            {
                "id": "search-related-work",
                "role": AgentRole.RESEARCHER.value,
                "task_template": (
                    "You are a Scholar conducting a comprehensive literature search for a peer review.\n\n"
                    "Paper to review:\n{input}\n\n"
                    "CRITICAL INSTRUCTIONS:\n"
                    "1. EXTRACT tool/framework names mentioned in the paper. Search for EACH one specifically.\n"
                    "2. Use your knowledge to identify COMPETING TOOLS in this domain. Search for EACH one.\n"
                    "   Look for DSLs, frameworks, libraries, or formal methods that solve similar problems.\n"
                    "3. Search for the paper TITLE to find citations and references.\n"
                    "4. Search for BROADER DOMAIN CONCEPTS relevant to the paper's topic.\n"
                    "5. For each paper found, record: title, authors, year, DOI/URL, how it relates to the reviewed paper.\n"
                    "6. CRITICAL: Only cite papers that appear in the search results. NEVER fabricate citations.\n\n"
                    "OUTPUT FORMAT — Produce your response using professional academic markdown with these exact sections:\n\n"
                    "## Search Queries Used\n"
                    "Bullet list of each search query executed, specifying the source for each.\n\n"
                    "## Related Papers Found\n"
                    "Present as a table with columns: #, Title, Authors, Year, Venue, Citations, Relevance to Reviewed Paper\n"
                    "Include at least 5-8 papers if available. Sort by relevance.\n\n"
                    "## Competing Tools and Approaches\n"
                    "Present as a table with columns: Tool/Framework, Domain, Description, Key Difference from Reviewed Paper\n"
                    "For each competing tool, explain what it does and how it differs from the reviewed paper.\n\n"
                    "## Novelty Assessment\n"
                    "Write a detailed assessment with subsections:\n"
                    "### Strengths of the Reviewed Work\n"
                    "### Gaps Addressed\n"
                    "### Remaining Gaps and Limitations\n"
                    "### Overall Novelty Rating: [High/Moderate/Low] — Justify this rating\n\n"
                    "## Research Gaps\n"
                    "Bullet list of specific research gaps addressed by the paper, with citations to relevant sources.\n\n"
                    "IMPORTANT: Use markdown tables, bold/italic formatting, and clear headers. "
                    "This will be exported as a professional PDF — format it accordingly."
                ),
            },
            {
                "id": "review-paper",
                "role": AgentRole.REVIEWER.value,
                "task_template": (
                    "You are a Paper Reviewer. Review the paper below thoroughly.\n\n"
                    "Paper:\n{input}\n\n"
                    "Execute your full review pipeline and produce your output using the following professional format:\n\n"
                    "## Paper Intake\n"
                    "Present a table with paper metadata: Title, Authors, Abstract (abbreviated), Paper Type (e.g., research/position/system), Key Sections.\n\n"
                    "## Structural Analysis\n"
                    "**Score**: X/10\n"
                    "Evaluate: IMRaD completeness, figure/table quality, writing clarity, logical flow.\n"
                    "Include a brief justification for the score.\n\n"
                    "## Claim Extraction and Evidence Mapping\n"
                    "Present a table with columns: #, Claim, Location in Paper, Evidence Strength (Strong/Moderate/Weak/Unsupported), Comments\n"
                    "Identify the top 5-7 most significant claims and map each to their supporting evidence.\n\n"
                    "## Methodology Verification\n"
                    "**Score**: X/10\n"
                    "Check: statistical rigor, reproducibility, experimental design, dataset adequacy, baselines used.\n"
                    "If applicable, note missing ablations or control experiments.\n\n"
                    "## Literature Grounding\n"
                    "**Score**: X/10\n"
                    "Compare against related work. Identify missing citations, competing tools not discussed, "
                    "gaps in the literature review. Reference specific papers from the search results.\n\n"
                    "## Adversarial Analysis\n"
                    "Bullet list covering:\n"
                    "- Logical flaws or inconsistencies found\n"
                    "- Missing experiments that would strengthen claims\n"
                    "- Alternative interpretations of the results\n"
                    "- Potential confounders or biases\n\n"
                    "## Synthesized Review\n"
                    "### Summary\n"
                    "2-3 paragraphs synthesizing the key findings.\n"
                    "### Strengths\n"
                    "Numbered list of strengths.\n"
                    "### Weaknesses\n"
                    "Numbered list of weaknesses.\n"
                    "### Missing Related Work\n"
                    "Reference specific papers from the prior search. Never fabricate.\n"
                    "### Minor Issues\n"
                    "Typographical, formatting, or presentation concerns.\n"
                    "### Recommendations to Authors\n"
                    "Actionable suggestions organized by priority.\n"
                    "### Overall Score\n"
                    "**X/10** — Include a brief justification."
                ),
            },
            {
                "id": "debate-review",
                "role": AgentRole.DEBATER.value,
                "task_template": (
                    "You are a Neutral Debate Moderator. The paper and its review have both been presented. "
                    "Run a structured debate to stress-test the review's criticisms against the paper's evidence.\n\n"
                    "REVIEW AND PAPER CONTEXT:\n{input}\n\n"
                    "Structure your response as three sections:\n\n"
                    "## 1. Paper Defense\n"
                    "For each major criticism in the review, present the paper's strongest possible defense with specific evidence. "
                    "Acknowledge valid criticisms.\n\n"
                    "## 2. Review Rebuttal\n"
                    "Evaluate each defense. Is the evidence sufficient? Are there gaps? "
                    "Identify criticisms from the review that the defense did not address.\n\n"
                    "## 3. Balanced Synthesis\n"
                    "Resolve disagreements. Identify points of agreement. "
                    "Provide a final recommendation: Accept / Minor Revision / Major Revision / Reject, with justification. "
                    "List required revisions and optional improvements."
                ),
            },
            {
                "id": "paper-review-writer",
                "role": AgentRole.WRITER.value,
                "task_template": (
                    "You are the Paper Review Writer. Transform the prior peer review stages below "
                    "into TWO polished, editorial-manager-ready documents in a single response: "
                    "a public Response to Authors (uploaded to the journal's public review field) "
                    "and a confidential Response to Editor (uploaded to the journal's confidential "
                    "comments field). The authors NEVER see the Response to Editor.\n\n"
                    "Inputs to draw on:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce a SINGLE self-contained markdown response with BOTH "
                    "documents, in this order, with `## ` (H2) headings so they can be split or rendered:\n\n"
                    "## Response to Authors\n"
                    "The public peer review with these exact sub-sections:\n"
                    "### Metadata\n"
                    "- **Manuscript Title**: <exact title from the paper>\n"
                    "- **Decision**: Accept / Minor Revision / Major Revision / Reject (pick one)\n\n"
                    "### 1. Summary\n"
                    "2-3 paragraphs: what the paper is about, key contributions, overall recommendation "
                    "and critical concerns. Be specific. Use the paper's own terminology. Bold the key findings.\n\n"
                    "### 2. Major Comments\n"
                    "Numbered list with bracket identifiers `[C1]`, `[C2]`, ... in priority order. For each: "
                    "state the problem, provide evidence (section/figure/table/claim/omission), suggest a fix. "
                    "Reference specific papers from the Scholar's search results when relevant. Aim for 3-5 comments.\n"
                    "Format: **[C1] <Short title>** — <1-2 sentences of context>. <Evidence + suggested fix.>\n\n"
                    "### 3. Minor Comments\n"
                    "Numbered list with bracket identifiers `[C1]`, `[C2]`, ... (numbering restarts). Typos, "
                    "figure legibility, terminology, missing references, missing clarifications. One or two "
                    "sentences each. Aim for 3-6 comments.\n\n"
                    "### 4. Recommendation\n"
                    "- **Decision**: <Accept / Minor Revision / Major Revision / Reject> (repeat metadata value)\n"
                    "- **Justification**: 2-3 sentences explaining WHY this decision. Reference major comments.\n\n"
                    "## Response to Editor\n"
                    "The AE-facing confidential note with these exact sub-sections:\n"
                    "### Metadata\n"
                    "- **Manuscript Title**: <exact title from the paper>\n"
                    "- **Recommendation**: Accept / Minor Revision / Major Revision / Reject (one word only)\n\n"
                    "### 1. Summary of Contribution\n"
                    "1-2 paragraphs: what the paper is about, main technical contributions, why they matter for the venue. "
                    "Do not include criticisms.\n\n"
                    "### 2. Key Strengths\n"
                    "Bulleted list of 2-4 strengths, each one sentence. Be specific (cite section/figure/table/concrete feature).\n\n"
                    "### 3. Key Concerns\n"
                    "Bulleted list of 2-4 concerns, each with bracket identifier `[C1]`, `[C2]`, ... in priority order. "
                    "For each: state the issue in one sentence, indicate whether blocking or non-blocking.\n"
                    "Format: **[C1] <Short title>** — <one sentence>. (blocking / non-blocking)\n\n"
                    "### 4. Recommendation and Justification\n"
                    "- **Recommendation**: <Accept / Minor Revision / Major Revision / Reject> (repeat metadata value)\n"
                    "- **Justification**: 2-3 sentences explaining WHY this recommendation. Weigh strengths vs. concerns. "
                    "Note whether the manuscript could become acceptable after revisions.\n\n"
                    "DO NOT fabricate citations. DO NOT add sections beyond those listed above. "
                    "Tone: Response to Authors is professional, respectful, constructive. "
                    "Response to Editor is direct, candid, suitable for an editor's eyes only."
                ),
            },
        ],
    },

}


class WorkflowExecuteRequest(BaseModel):
    workflow_id: str
    input: str | None = None
    paper_id: UUID | None = None
    agent_assignments: dict[str, UUID]
    include_full_paper: bool = True
    rubric_standard: str = "general"
    review_text: str | None = None


class WorkflowExecuteResponse(BaseModel):
    workflow_id: str
    workflow_name: str
    stages: list[dict]


class WorkflowStartResponse(BaseModel):
    execution_id: UUID
    status: str
    workflow_id: str
    workflow_name: str


async def _get_user_config_by_id(db: AsyncSession, user_id: str, config_id: UUID) -> AgentConfig | None:
    result = await db.execute(
        select(AgentConfig)
        .options(selectinload(AgentConfig.skills))
        .where(
            AgentConfig.user_id == user_id,
            AgentConfig.id == config_id,
        )
    )
    return result.scalar_one_or_none()


def _sanitize_output(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL)
    text = re.sub(r"\n{3,}", "\n\n", text)       # 3+ newlines → paragraph break
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r" {5,}", "  ", text)           # collapse excessive spaces (keep ≤4 for code blocks)
    text = re.sub(r"\t{3,}", "\t", text)
    return text.strip()


def _validate_dual_section_output(
    output: str,
    required_sections: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """Check that *output* contains all *required_sections*.

    Returns ``(is_valid, missing_sections)`` where *missing_sections* lists
    the section headings not found (case-insensitive substring match).
    When *required_sections* is ``None``, defaults to the paper-review-writer
    pair for backward compatibility.
    """
    if required_sections is None:
        required_sections = ["## Response to Authors", "## Response to Editor"]
    lower_output = output.lower()
    missing = [s for s in required_sections if s.lower() not in lower_output]
    return len(missing) == 0, missing


async def _next_progress_event_id(
    pm: ProgressManager, execution_id: UUID | str
) -> int:
    key = str(execution_id)
    lock = await pm._lock_for(key)
    async with lock:
        return pm._next_id(key)


async def _run_stage(
    db: AsyncSession,
    user_id: str,
    stage_def: dict,
    context: str,
    config_id: UUID,
    pdf_bytes: Optional[bytes] = None,
    paper_s2_id: str | None = None,
    topic_query: str | None = None,
    paper_content: str | None = None,
    rubric_standard: str = "general",
    research_dossier=None,
    grobid_dict: dict | None = None,
    progress_manager: Optional[ProgressManager] = None,
    execution_id: Optional[UUID] = None,
) -> dict:
    config = await _get_user_config_by_id(db, user_id, config_id)
    if not config:
        return {
            "agent_role": stage_def["role"],
            "status": "skipped",
            "output": f"Agent config '{config_id}' not found for this user.",
        }

    skill_prompts = []
    for s in config.skills:
        if s.prompt_template:
            skill_prompts.append(s.prompt_template)
    skill_tools = config.get_tool_names()

    from app.tools import get_tools_by_names
    resolved_tools = get_tools_by_names(skill_tools)

    system_prompt = config.system_prompt or ""
    if skill_prompts:
        system_prompt += "\n\nAdditional knowledge:\n" + "\n---\n".join(skill_prompts)

    agent_type = config.role.value if hasattr(config.role, "value") else config.role

    variant_raw = getattr(config, "variant", None)
    variant_value = variant_raw.value if hasattr(variant_raw, "value") else variant_raw

    agent = create_agent(
        agent_type=agent_type,
        model=config.model,
        provider=config.provider,
        strategy=config.strategy.value if hasattr(config.strategy, "value") else (config.strategy or "direct"),
        system_prompt=system_prompt,
        tools=resolved_tools,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        variant=variant_value,
    )

    task = stage_def["task_template"].format(input=context)

    if pdf_bytes and model_supports_pdf(str(config.model)):
        messages = [create_multimodal_human_message(pdf_bytes, task)]
    else:
        messages = [HumanMessage(content=task)]

    agent_context = {}
    if pdf_bytes:
        agent_context["pdf_bytes"] = pdf_bytes
    if paper_s2_id:
        agent_context["paper_s2_id"] = paper_s2_id
    if topic_query:
        agent_context["topic_query"] = topic_query
    if paper_content:
        agent_context["paper_content"] = paper_content
        print(
            f"[_run_stage] stage={stage_def.get('role', '?')} paper_content={len(paper_content)} chars",
            flush=True,
        )
    else:
        print(
            f"[_run_stage] stage={stage_def.get('role', '?')} NO paper_content passed",
            flush=True,
        )
    if rubric_standard:
        agent_context["rubric_standard"] = rubric_standard
    if research_dossier:
        agent_context["research_dossier"] = research_dossier
    if grobid_dict:
        agent_context["grobid"] = grobid_dict

    if stage_def.get("role") == "researcher":
        agent_context["skip_synthesis"] = True

    max_retries = 3
    last_error = None
    for attempt in range(max_retries):
        try:
            run_kwargs: dict[str, Any] = {"context": agent_context}
            if progress_manager is not None:
                run_kwargs["progress_manager"] = progress_manager
            if execution_id is not None:
                run_kwargs["execution_id"] = execution_id
            result = await asyncio.wait_for(
                agent.run(messages, **run_kwargs),
                timeout=STAGE_TIMEOUT_SECONDS,
            )
            usage = result.get("metadata", {}).get("usage", {})
            input_tokens = usage.get("input_tokens", 0) or 0
            output_tokens = usage.get("output_tokens", 0) or 0
            total_tokens = usage.get("total_tokens", 0) or 0

            model_name = str(config.model) if config.model else ""
            pricing = await fetch_model_pricing()
            cost = calculate_cost(model_name, input_tokens, output_tokens, pricing)

            metadata = result.get("metadata", {})
            metadata["usage"] = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "model": model_name,
                "cost_usd": round(cost, 8),
            }
            metadata["agent_role"] = stage_def["role"]
            metadata["agent_name"] = config.name

            # --- Section-delimiter validation for paper-review-writer ---
            if stage_def.get("id") == "paper-review-writer":
                output_text = result.get("output", "") or ""
                is_valid, missing = _validate_dual_section_output(output_text)
                if not is_valid:
                    # Retry once with a reminder
                    reminder = (
                        "Your previous response was missing the following required section(s): "
                        f"{', '.join(missing)}. Please produce BOTH sections "
                        "(`## Response to Authors` and `## Response to Editor`) in your next response."
                    )
                    try:
                        retry_kwargs: dict[str, Any] = {"context": agent_context}
                        if progress_manager is not None:
                            retry_kwargs["progress_manager"] = progress_manager
                        if execution_id is not None:
                            retry_kwargs["execution_id"] = execution_id
                        retry_result = await asyncio.wait_for(
                            agent.run([HumanMessage(content=reminder)], **retry_kwargs),
                            timeout=STAGE_TIMEOUT_SECONDS,
                        )
                        retry_output = retry_result.get("output", "") or ""
                        result = retry_result  # use retry result going forward
                        is_valid2, missing2 = _validate_dual_section_output(retry_output)
                        if not is_valid2:
                            metadata["validation_warning"] = (
                                f"missing section(s) after retry: {', '.join(missing2)}"
                            )
                    except Exception as retry_err:
                        logger.warning(f"Validation retry failed: {retry_err}")
                        metadata["validation_warning"] = (
                            f"missing section(s) and retry failed: {', '.join(missing)}"
                        )

            rating = result.get("context", {}).get("rating")
            dossier = result.get("context", {}).get("research_dossier")

            # Only run rubric evaluation on review stages, not search/debate/writer stages
            is_review_stage = (
                stage_def.get("role") == "reviewer"
                or stage_def.get("id") == "review-paper"
            )
            if not rating and rubric_standard and rubric_standard != "none" and is_review_stage:
                review_text = _sanitize_output(result.get("output", ""))
                if review_text:
                    try:
                        eval_llm = llm_service.get_llm(
                            model=config.model,
                            provider=config.provider,
                            temperature=0.3,
                            max_tokens=2048,
                        )
                        rating = await evaluate_rubric(
                            llm=eval_llm,
                            review_text=review_text,
                            rubric_standard=rubric_standard,
                            system_prompt="You are an expert academic rubric evaluator. Score the review objectively.",
                        )
                    except Exception as e:
                        logger.warning(f"Rubric evaluation failed: {e}")
                        rating = None

            return {
                "agent_role": stage_def["role"],
                "agent_name": config.name,
                "status": "completed",
                "output": _sanitize_output(result.get("output", "")),
                "metadata": metadata,
                "rating": rating,
                "research_dossier": dossier,
            }
        except asyncio.TimeoutError:
            logger.warning(f"Stage for role {stage_def['role']} timed out after {STAGE_TIMEOUT_SECONDS}s")
            return {
                "agent_role": stage_def["role"],
                "agent_name": config.name,
                "status": "timeout",
                "output": f"Stage timed out after {STAGE_TIMEOUT_SECONDS} seconds. Previous stage output preserved.",
                "metadata": {"timeout_seconds": STAGE_TIMEOUT_SECONDS, "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "model": str(config.model) if config.model else "", "cost_usd": 0.0}},
            }
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "429" in error_str or "RateLimitError" in error_str or "rate limit" in error_str.lower():
                wait = (2 ** attempt) * 10
                logger.warning(f"Stage {stage_def['role']} rate limited (attempt {attempt + 1}/{max_retries}), waiting {wait}s...")
                await asyncio.sleep(wait)
                continue
            break

    logger.error(
        f"Stage for role {stage_def['role']} failed: {last_error}",
        exc_info=last_error,
    )
    return {
        "agent_role": stage_def["role"],
        "agent_name": config.name,
        "status": "error",
        "output": f"Stage failed: {type(last_error).__name__}: {str(last_error)[:500]}",
        "metadata": {"error_type": type(last_error).__name__, "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "model": str(config.model) if config.model else "", "cost_usd": 0.0}},
    }


async def _fetch_paper_content(db: AsyncSession, user_id: str, paper_id: UUID) -> PaperContent:
    result = await db.execute(
        select(Paper).where(Paper.id == paper_id, Paper.owner_id == user_id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    POLL_INTERVAL = 1.0
    POLL_TIMEOUT = int(os.environ.get("PAPER_PROCESSING_TIMEOUT", "60"))
    elapsed = 0.0
    while paper.processing_status in ("pending", "processing") and elapsed < POLL_TIMEOUT:
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        result = await db.execute(
            select(Paper).where(Paper.id == paper_id, Paper.owner_id == user_id)
        )
        paper = result.scalar_one_or_none()
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    if paper.processing_status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Paper processing failed. Cannot perform review.",
        )
    if paper.processing_status in ("pending", "processing"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Paper still processing after timeout ({POLL_TIMEOUT}s). Try again shortly.",
        )

    parts = []
    if paper.title:
        parts.append(f"Title: {paper.title}")
    if paper.authors:
        parts.append(f"Authors: {', '.join(paper.authors)}")
    if paper.abstract:
        parts.append(f"Abstract: {paper.abstract}")

    if paper.analysis:
        analysis = paper.analysis
        if analysis.get("keywords"):
            parts.append(f"Keywords: {', '.join(analysis['keywords'])}")
        if analysis.get("scientific_areas"):
            parts.append(f"Scientific Areas: {', '.join(analysis['scientific_areas'])}")
        if analysis.get("auto_tags"):
            parts.append(f"Auto Tags: {', '.join(analysis['auto_tags'])}")
        if analysis.get("field_of_study"):
            parts.append(f"Field: {analysis['field_of_study']}")
        if analysis.get("subfield"):
            parts.append(f"Subfield: {analysis['subfield']}")

    chunks_result = await db.execute(
        select(PaperChunk)
        .where(PaperChunk.paper_id == paper_id)
        .order_by(PaperChunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()
    if chunks:
        full_text = "\n\n".join(c.text for c in chunks)
        parts.append(f"Full Text:\n{full_text}")
    elif paper.minio_key:
        # Graceful fallback: re-extract text from PDF for papers without chunks
        # (e.g. uploaded before chunking was implemented)
        logger.warning(f"No chunks for paper {paper_id}, extracting from PDF on-the-fly")
        try:
            from app.services.minio_service import minio_service
            from app.services.pdf_service import pdf_service

            pdf_bytes = await minio_service.download_file(paper.minio_key)
            extracted = await pdf_service.extract_text(pdf_bytes)
            if extracted and extracted.full_text:
                parts.append(f"Full Text:\n{extracted.full_text}")
        except Exception as e:
            logger.warning(f"Failed to extract text from PDF for paper {paper_id}: {e}")

    text = "\n\n".join(parts)

    pdf_bytes: Optional[bytes] = None
    if paper.minio_key:
        try:
            from app.services.minio_service import minio_service
            pdf_bytes = await minio_service.download_file(paper.minio_key)
        except Exception as e:
            logger.warning(f"Failed to download PDF from MinIO for paper {paper_id}: {e}")

    return PaperContent(text=text, pdf_bytes=pdf_bytes)


def _extract_metadata(full_input: str) -> str:
    """Extract metadata (title, authors, abstract, keywords) from full paper input.

    The full input format is:
        Title: ...
        Authors: ...
        Abstract: ...
        Keywords: ...
        Full Text:
        ...

    Returns everything before 'Full Text:' if present, otherwise the full input.
    """
    marker = "\n\nFull Text:"
    idx = full_input.find(marker)
    if idx != -1:
        return full_input[:idx]
    return full_input


def _build_stage_context(
    original_input: str,
    prior_findings: list[dict],
    model: str | None = None,
    output_tokens: int = 4096,
    has_separate_paper_content: bool = False,
) -> str:
    if not prior_findings:
        if has_separate_paper_content:
            return _extract_metadata(original_input)
        return original_input

    budgets = budget_for_stages(model=model, output_tokens=output_tokens)
    paper_budget = budgets["paper_content"]
    prior_budget = budgets["prior_stages"]

    if has_separate_paper_content:
        # Agent gets full paper via agent_context — keep context lean with metadata only
        paper_fitted = _extract_metadata(original_input)
    else:
        paper_fitted = fit_to_budget(original_input, paper_budget, label="paper")

    parts = [f"PAPER / INPUT:\n{paper_fitted}"]
    parts.append("\n--- PRIOR STAGE OUTPUTS ---\n")
    per_stage = max(prior_budget // max(len(prior_findings), 1), 500)
    for finding in prior_findings:
        fitted = fit_to_budget(finding["output"], per_stage, label=f"stage:{finding['stage']}")
        parts.append(f"[Stage: {finding['stage']} | Role: {finding['role']} | Agent: {finding['agent_name']}]\n{fitted}\n")
    return "\n".join(parts)


async def _ensure_review_writer_config(db: AsyncSession, user_id: str) -> None:
    """Ensure a Review Writer AgentConfig exists for this user.

    Existing users created before the Review Writer seed was added may be
    missing this config. Creates it on-demand without requiring re-login.
    """
    from uuid import UUID
    from sqlalchemy import select
    from app.models import AgentConfig, AgentRole, Skill
    from app.seeds.scholarflow_skills import _AGENT_SEEDS

    # 1. Convert user_id to UUID if needed
    user_id_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

    # 2. Check if config already exists — short-circuit
    result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.user_id == user_id_uuid,
            AgentConfig.role == AgentRole.WRITER,
            AgentConfig.name == "Review Writer",
            AgentConfig.name == "Review Writer",
        )
    )
    if result.scalar_one_or_none():
        return

    # 3. Find the Review Writer seed entry
    seed = None
    for s in _AGENT_SEEDS:
        if s["name"] == "Review Writer":
            seed = s
            break
    if not seed:
        return  # safety: seed not found, nothing to create

    # 4. Look up the required skills for this user
    result = await db.execute(
        select(Skill).where(
            Skill.user_id == user_id_uuid,
            Skill.name.in_(seed["skill_names"]),
        )
    )
    skills = {s.name: s for s in result.scalars().all()}
    if any(n not in skills for n in seed["skill_names"]):
        return  # safety: skills missing, user must re-login to trigger seed

    # 5. Create the AgentConfig
    config = AgentConfig(
        user_id=user_id_uuid,
        name=seed["name"],
        role=seed["role"],
        provider=seed["provider"],
        model=seed["model"],
        strategy=seed["strategy"],
        system_prompt=seed["system_prompt"],
        temperature=0.7,
        max_tokens=4096,
        tools=[],
        is_default=False,
    )
    db.add(config)
    await db.flush()  # get config.id

    # 6. Associate skills via the M2M table
    for skill_name in seed["skill_names"]:
        skill = skills[skill_name]
        await db.execute(
            agent_skills_table.insert().values(
                agent_config_id=config.id,
                skill_id=skill.id,
            )
        )

    await db.commit()


@router.post("/execute")
async def execute_workflow(
    req: WorkflowExecuteRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.workflow_id not in WORKFLOW_DEFINITIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown workflow: {req.workflow_id}",
        )

    workflow = WORKFLOW_DEFINITIONS[req.workflow_id]

    # Ensure Review Writer agent config exists for this user
    await _ensure_review_writer_config(db, user_id)

    if not req.paper_id and not req.input:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either input or paper_id must be provided",
        )

    paper_content: Optional[PaperContent] = None
    pdf_bytes: Optional[bytes] = None
    paper_s2_id: Optional[str] = None
    topic_query: Optional[str] = None
    if req.paper_id:
        paper_content = await _fetch_paper_content(db, user_id, req.paper_id)
        context = paper_content.text
        pdf_bytes = paper_content.pdf_bytes

        if req.review_text:
            context = f"PAPER:\n{context}\n\nREVIEW TO ANALYZE:\n{req.review_text}"
        elif req.input:
            context = f"{context}\n\n## Custom Instructions\n{req.input}"

        paper_result = await db.execute(
            select(Paper).where(Paper.id == req.paper_id, Paper.owner_id == user_id)
        )
        paper = paper_result.scalar_one_or_none()
        if paper:
            if paper.doi:
                paper_s2_id = f"DOI:{paper.doi}"
            elif paper.arxiv_id:
                paper_s2_id = f"ARXIV:{paper.arxiv_id}"
            parts = []
            if paper.title:
                parts.append(paper.title)
            if paper.analysis and paper.analysis.get("keywords"):
                parts.extend(paper.analysis["keywords"][:3])
            topic_query = " ".join(parts) if parts else None
    elif req.input:
        context = req.input
        topic_query = req.input[:200] if len(req.input) > 200 else req.input

    stage_placeholders = [
        {
            "agent_role": s["role"],
            "agent_name": "",
            "status": "pending",
            "output": "",
            "metadata": {},
        }
        for s in workflow["stages"]
    ]

    execution = WorkflowExecution(
        user_id=user_id,
        workflow_id=req.workflow_id,
        workflow_name=workflow["name"],
        input_text=req.input,
        paper_id=req.paper_id,
        agent_assignments={k: str(v) for k, v in req.agent_assignments.items()},
        stages=stage_placeholders,
        status="running",
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    execution_id = str(execution.id)

    paper_content_to_pass = context if req.include_full_paper and req.paper_id else None

    try:
        pool = await get_arq_pool()
        job = await pool.enqueue_job(
            "execute_workflow_task",
            execution_id=execution_id,
            user_id=str(user_id),
            workflow_id=req.workflow_id,
            original_context=context,
            pdf_bytes=pdf_bytes,
            paper_s2_id=paper_s2_id,
            topic_query=topic_query,
            agent_assignments={k: str(v) for k, v in req.agent_assignments.items()},
            paper_content=paper_content_to_pass,
            rubric_standard=req.rubric_standard,
        )
        if job:
            logger.info(f"Workflow {execution_id} enqueued as ARQ job {job.job_id}")
    except Exception as e:
        logger.error(f"Failed to enqueue workflow {execution_id}: {e}")
        execution.status = "error"
        await db.commit()
        raise HTTPException(status_code=503, detail=f"Task queue unavailable: {e}")

    return WorkflowStartResponse(
        execution_id=execution.id,
        status="running",
        workflow_id=req.workflow_id,
        workflow_name=workflow["name"],
    )


@router.get("/")
async def list_workflows():
    return [
        {
            "id": wf_id,
            "name": wf["name"],
            "stages": len(wf["stages"]),
            "roles": [s["role"] for s in wf["stages"]],
            "stage_ids": [s["id"] for s in wf["stages"]],
        }
        for wf_id, wf in WORKFLOW_DEFINITIONS.items()
    ]


@router.get("/results", response_model=list)
async def list_workflow_results(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.user_id == user_id)
        .order_by(desc(WorkflowExecution.created_at))
        .limit(50)
    )
    executions = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "workflow_id": e.workflow_id,
            "workflow_name": e.workflow_name,
            "input_text": e.input_text,
            "paper_id": str(e.paper_id) if e.paper_id else None,
            "agent_assignments": e.agent_assignments,
            "stages": e.stages,
            "status": e.status,
            "duration_seconds": e.duration_seconds,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in executions
    ]


@router.delete("/results/{execution_id}")
async def delete_workflow_result(
    execution_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.id == execution_id, WorkflowExecution.user_id == user_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    sessions_result = await db.execute(
        select(RevisionSession.id).where(RevisionSession.workflow_execution_id == execution_id)
    )
    session_ids = [row[0] for row in sessions_result.all()]
    if session_ids:
        await db.execute(
            select(RevisionMessage).where(RevisionMessage.revision_session_id.in_(session_ids))
        )
        for sid in session_ids:
            msg_result = await db.execute(
                select(RevisionMessage).where(RevisionMessage.revision_session_id == sid)
            )
            for msg in msg_result.scalars().all():
                await db.delete(msg)
        for sid in session_ids:
            sess_result = await db.execute(
                select(RevisionSession).where(RevisionSession.id == sid)
            )
            sess = sess_result.scalar_one_or_none()
            if sess:
                await db.delete(sess)
    await db.delete(execution)
    await db.commit()
    return {"status": "deleted", "id": str(execution_id)}


@router.post("/cancel/{execution_id}")
async def cancel_workflow(
    execution_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.id == execution_id, WorkflowExecution.user_id == user_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    if execution.status not in ("running", "pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel execution with status '{execution.status}'",
        )

    await set_cancel(str(execution_id))
    execution.status = "cancelling"
    await db.commit()

    return {"status": "cancelling", "id": str(execution_id)}


@router.get("/results/{execution_id}")
async def get_workflow_result(
    execution_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.id == execution_id, WorkflowExecution.user_id == user_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return {
        "id": str(execution.id),
        "workflow_id": execution.workflow_id,
        "workflow_name": execution.workflow_name,
        "input_text": execution.input_text,
        "paper_id": str(execution.paper_id) if execution.paper_id else None,
        "agent_assignments": execution.agent_assignments,
        "stages": execution.stages,
        "status": execution.status,
        "duration_seconds": execution.duration_seconds,
        "created_at": execution.created_at.isoformat() if execution.created_at else None,
    }


@router.get("/results/{execution_id}/stream")
async def stream_workflow_progress(
    execution_id: UUID,
    request: Request,
    user_id: str = Depends(get_current_user_from_query),
    db: AsyncSession = Depends(get_db),
):
    """SSE stream of execution events (replay from ``Last-Event-ID`` then live)."""
    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.id == execution_id,
            WorkflowExecution.user_id == user_id,
        )
    )
    execution = result.scalar_one_or_none()
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    if execution.status in TERMINAL_EXECUTION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Execution already {execution.status}. Use /snapshot endpoint for history.",
        )

    last_event_id_header = request.headers.get("Last-Event-ID", "0")
    try:
        last_event_id = int(last_event_id_header)
    except (TypeError, ValueError):
        last_event_id = 0

    progress_manager = get_progress_manager()

    terminal_types = (EventType.EXECUTION_COMPLETED, EventType.EXECUTION_FAILED)

    async def event_stream():
        yield ": connected\n\n"
        replayed = await progress_manager.get_events(execution_id, after_event_id=last_event_id)
        for ev in replayed:
            yield f"id: {ev.event_id}\ndata: {ev.to_json()}\n\n"

        local_queue: asyncio.Queue = asyncio.Queue()
        relay_done = asyncio.Event()

        async def relay_events() -> None:
            try:
                async for ev in progress_manager.subscribe(execution_id):
                    await local_queue.put(ev)
                    if ev.event_type in terminal_types:
                        return
            finally:
                relay_done.set()

        async def relay_redis_events() -> None:
            try:
                async for ev in progress_manager.subscribe_redis(execution_id):
                    await local_queue.put(ev)
                    if ev.event_type in terminal_types:
                        return
            except Exception:
                pass

        relay_task = asyncio.create_task(relay_events())
        redis_task = asyncio.create_task(relay_redis_events())
        try:
            while True:
                try:
                    ev = await asyncio.wait_for(
                        local_queue.get(),
                        timeout=HEARTBEAT_INTERVAL_SECONDS,
                    )
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield f"id: {ev.event_id}\ndata: {ev.to_json()}\n\n"
                if ev.event_type in terminal_types:
                    break
        finally:
            relay_task.cancel()
            redis_task.cancel()
            try:
                await relay_task
                await redis_task
            except (asyncio.CancelledError, Exception):
                pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/results/{execution_id}/snapshot",
    response_model=WorkflowExecutionSnapshotResponse,
)
async def get_workflow_snapshot(
    execution_id: UUID,
    user_id: str = Depends(get_current_user_from_query),
    db: AsyncSession = Depends(get_db),
):
    """Historical replay of all persisted events for a completed execution."""
    from app.models.workflow_event import WorkflowEvent

    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.id == execution_id,
            WorkflowExecution.user_id == user_id,
        )
    )
    execution = result.scalar_one_or_none()
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    events_result = await db.execute(
        select(WorkflowEvent)
        .where(WorkflowEvent.execution_id == execution_id)
        .order_by(WorkflowEvent.event_id.asc())
    )
    rows = events_result.scalars().all()

    events = [
        ExecutionEventSchema(
            event_id=row.event_id,
            execution_id=row.execution_id,
            event_type=row.event_type,
            timestamp=row.timestamp,
            data=row.data or {},
        )
        for row in rows
    ]

    return WorkflowExecutionSnapshotResponse(
        events=events,
        execution=WorkflowExecutionResponse.model_validate(execution),
    )


@router.delete("/results")
async def delete_all_workflow_results(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.user_id == user_id)
    )
    executions = result.scalars().all()
    count = len(executions)
    if executions:
        exec_ids = [e.id for e in executions]
        sessions_result = await db.execute(
            select(RevisionSession.id).where(RevisionSession.workflow_execution_id.in_(exec_ids))
        )
        session_ids = [row[0] for row in sessions_result.all()]
        if session_ids:
            msgs_result = await db.execute(
                select(RevisionMessage).where(RevisionMessage.revision_session_id.in_(session_ids))
            )
            for msg in msgs_result.scalars().all():
                await db.delete(msg)
            sess_result = await db.execute(
                select(RevisionSession).where(RevisionSession.id.in_(session_ids))
            )
            for sess in sess_result.scalars().all():
                await db.delete(sess)
    for e in executions:
        await db.delete(e)
    await db.commit()
    return {"status": "deleted", "count": count}


PDF_STYLES = """
<style>
  @page {
    margin: 2cm 2.5cm;
    size: A4;
  }
  body {
    font-family: 'Helvetica', 'Arial', sans-serif;
    font-size: 10.5pt;
    line-height: 1.65;
    color: #1a1a1a;
    max-width: 160mm;
    margin: 0 auto;
    padding: 0;
  }
  h1 {
    font-size: 20pt;
    color: #1a365d;
    border-bottom: 2.5px solid #2b6cb0;
    padding-bottom: 8px;
    margin-top: 0;
    margin-bottom: 16px;
    page-break-before: avoid;
  }
  h2 {
    font-size: 14pt;
    color: #2c5282;
    margin-top: 24px;
    margin-bottom: 10px;
    page-break-before: avoid;
  }
  h3 {
    font-size: 12pt;
    color: #2d3748;
    margin-top: 18px;
    margin-bottom: 8px;
    page-break-before: avoid;
  }
  h4 {
    font-size: 11pt;
    color: #4a5568;
    margin-top: 14px;
    margin-bottom: 6px;
  }
  p {
    margin: 8px 0;
    text-align: justify;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
  }
  th {
    background-color: #edf2f7;
    color: #1a365d;
    padding: 7px 10px;
    text-align: left;
    font-weight: 700;
    border: 1px solid #cbd5e0;
    font-size: 9.5pt;
  }
  td {
    padding: 6px 10px;
    border: 1px solid #cbd5e0;
    vertical-align: top;
  }
  tr:nth-child(even) td {
    background-color: #f7fafc;
  }
  code {
    background-color: #edf2f7;
    padding: 1px 5px;
    border-radius: 3px;
    font-family: 'Courier New', 'Courier', monospace;
    font-size: 9pt;
  }
  pre {
    background-color: #1a202c;
    color: #e2e8f0;
    padding: 10px 14px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 12px 0;
    font-size: 9pt;
    line-height: 1.4;
    page-break-inside: avoid;
  }
  pre code {
    background-color: transparent;
    padding: 0;
    color: inherit;
    font-size: inherit;
  }
  blockquote {
    border-left: 4px solid #4299e1;
    margin: 12px 0;
    padding: 6px 14px;
    background-color: #ebf8ff;
    color: #2c5282;
  }
  ul, ol {
    margin: 6px 0;
    padding-left: 22px;
  }
  li {
    margin: 3px 0;
  }
  strong {
    font-weight: 700;
    color: #1a1a1a;
  }
  em {
    font-style: italic;
  }
  hr {
    border: none;
    border-top: 1.5px solid #e2e8f0;
    margin: 24px 0;
  }
  .status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 9pt;
    font-weight: 700;
  }
  .status-completed { background-color: #c6f6d5; color: #22543d; }
  .status-partial { background-color: #fefcbf; color: #744210; }
  .status-failed { background-color: #fed7d7; color: #822727; }
  .status-timeout { background-color: #fed7d7; color: #822727; }
  .status-error { background-color: #fed7d7; color: #822727; }
  .status-skipped { background-color: #e2e8f0; color: #4a5568; }
  .meta-label {
    font-weight: 700;
    color: #4a5568;
  }
  .input-section {
    background-color: #f7fafc;
    padding: 12px 16px;
    border-left: 3px solid #4299e1;
    margin: 12px 0;
    font-size: 10pt;
  }
  .footer {
    text-align: center;
    color: #a0aec0;
    font-size: 8.5pt;
    margin-top: 32px;
    border-top: 1px solid #e2e8f0;
    padding-top: 12px;
  }
</style>
"""


def _build_markdown_from_execution(execution: WorkflowExecution) -> str:
    lines = []
    lines.append(f"# {execution.workflow_name}")

    status_icon = {
        "completed": "✅",
        "partial": "⚠️",
        "failed": "❌",
        "timeout": "⏰",
        "error": "❌",
        "skipped": "⏭️",
    }.get(execution.status, "❓")
    lines.append("")
    lines.append(f"**{status_icon} Status:** `{execution.status}`")
    if execution.duration_seconds:
        lines.append(f"**⏱ Duration:** {execution.duration_seconds:.1f} seconds")
    if execution.created_at:
        lines.append(f"**📅 Generated:** {execution.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    if execution.input_text:
        lines.append("## 📋 Input")
        lines.append("")
        lines.append(execution.input_text)
        lines.append("")
        lines.append("---")
        lines.append("")

    # Stage-by-stage results
    if execution.stages:
        lines.append("## 📑 Stage Results")
        lines.append("")

        for i, stage in enumerate(execution.stages, 1):
            role = stage.get("agent_role", "Unknown").replace("_", " ").title()
            agent_name = stage.get("agent_name", "")
            stage_status = stage.get("status", "unknown")

            status_indicators = {
                "completed": "✅ **Completed**",
                "partial": "⚠️ **Partial**",
                "failed": "❌ **Failed**",
                "timeout": "⏰ **Timeout**",
                "error": "❌ **Error**",
                "skipped": "⏭️ **Skipped**",
            }
            status_text = status_indicators.get(stage_status, f"**{stage_status}**")
            duration = stage.get("metadata", {}).get("duration_seconds")
            dur_str = f" ({duration:.1f}s)" if duration else ""

            title = f"### Stage {i}: {role}"
            if agent_name:
                title += f" — {agent_name}"
            lines.append(title)
            lines.append(f"*{status_text}*{dur_str}")
            lines.append("")

            output = _sanitize_output(stage.get("output", ""))
            if output:
                lines.append(output)
            else:
                lines.append("*No output generated.*")
            lines.append("")

            if i < len(execution.stages):
                lines.append("---")
                lines.append("")

    lines.append("---")
    lines.append(f"*Generated by AcademicPal — {execution.workflow_name}*")
    return "\n".join(lines)


@router.get("/results/{execution_id}/export/markdown")
async def export_workflow_markdown(
    execution_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export workflow result as a markdown file."""
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.id == execution_id, WorkflowExecution.user_id == user_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    md_content = _build_markdown_from_execution(execution)
    filename = f"{execution.workflow_name.lower().replace(' ', '_')}_{execution.id}.md"

    return StreamingResponse(
        io.BytesIO(md_content.encode("utf-8")),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/results/{execution_id}/export/pdf")
async def export_workflow_pdf(
    execution_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export workflow result as a PDF file."""
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.id == execution_id, WorkflowExecution.user_id == user_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    try:
        import markdown as md_lib
        from weasyprint import HTML as WeasyprintHTML
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation library not available: {e}",
        )

    md_content = _build_markdown_from_execution(execution)
    html_body = md_lib.markdown(md_content, extensions=["tables", "fenced_code", "codehilite"])

    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{PDF_STYLES}
</head>
<body>
{html_body}
<div class="footer">Generated by AcademicPal — {execution.workflow_name}</div>
</body>
</html>"""

    try:
        pdf_bytes = WeasyprintHTML(string=full_html).write_pdf()
    except Exception as e:
        logger.exception("WeasyPrint PDF rendering failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF rendering failed: {e}",
        )

    filename = f"{execution.workflow_name.lower().replace(' ', '_')}_{execution.id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pricing")
async def get_model_pricing():
    pricing = await fetch_model_pricing()
    return {"pricing": pricing}


@router.get("/rubrics")
async def list_rubric_standards():
    from app.services.rubric_standards import list_rubric_standards as _list
    return {"standards": _list()}


@router.get("/rubrics/detect")
async def detect_rubric(
    paper_id: UUID | None = None,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.rubric_standards import detect_rubric_from_paper
    if not paper_id:
        return {"standard": "general"}
    result = await db.execute(
        select(Paper).where(Paper.id == paper_id, Paper.owner_id == user_id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        return {"standard": "general"}
    return {"standard": detect_rubric_from_paper(paper.venue, paper.doi, paper.arxiv_id)}
