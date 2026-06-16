import asyncio
import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from langchain_core.messages import HumanMessage

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, AgentConfig, Paper, PaperChunk, AgentRole, WorkflowExecution
from app.agents.factory import create_agent
from app.utils.context_budget import get_context_budget, fit_to_budget, budget_for_stages

STAGE_TIMEOUT_SECONDS = 300.0
STAGE_DELAY_SECONDS = 15

logger = logging.getLogger(__name__)

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
                    "Output format:\n"
                    "## Search Queries Used\n[List the queries you searched]\n\n"
                    "## Related Papers Found\n[For each paper: Title, Authors, Year, Source, DOI/URL, Relevance]\n\n"
                    "## Competing Tools/Approaches\n[List tools and frameworks that address similar problems]\n\n"
                    "## Novelty Assessment\n[How does this paper compare to existing work?]\n\n"
                    "## Research Gaps\n[What gaps does this paper address?]"
                ),
            },
            {
                "id": "review-paper",
                "role": AgentRole.REVIEWER.value,
                "task_template": (
                    "You are a Paper Reviewer. Review the paper below thoroughly.\n\n"
                    "Paper:\n{input}\n\n"
                    "Execute your full review pipeline:\n"
                    "1. INTAKE: Extract title, authors, abstract, paper type, key sections\n"
                    "2. STRUCTURAL ANALYSIS: Evaluate IMRaD completeness, figure/table quality, writing quality\n"
                    "3. CLAIM EXTRACTION: Identify top 5 claims with evidence strength (Strong/Moderate/Weak/Unsupported)\n"
                    "4. METHODOLOGY VERIFICATION: Check statistical rigor, reproducibility, experimental design\n"
                    "5. LITERATURE GROUNDING: Compare against related work found in Stage 1. "
                    "Identify missing citations, competing tools not discussed, and gaps in the literature review.\n"
                    "6. ADVERSARIAL RED TEAM: Challenge claims, find logical flaws, identify missing experiments\n"
                    "7. SYNTHESIS: Produce a single consolidated review with:\n"
                    "   (a) Summary\n"
                    "   (b) Strengths\n"
                    "   (c) Weaknesses\n"
                    "   (d) Missing Related Work (cite specific papers from Stage 1)\n"
                    "   (e) Minor Issues\n"
                    "   (f) Recommendations to Authors\n"
                    "   (g) Overall Score (1-10)\n\n"
                    "CRITICAL: When citing papers in Related Work, use ONLY papers found in Stage 1 search results. "
                    "Never fabricate citations. If you cannot find specific competing tools, state that explicitly."
                ),
            },
            {
                "id": "refine-review",
                "role": AgentRole.WRITER.value,
                "task_template": (
                    "You are an Academic Writer. Transform the raw review below into a polished, professional peer review.\n\n"
                    "Review to refine:\n{input}\n\n"
                    "Produce a structured review with these sections:\n\n"
                    "## Reviewer Summary\n"
                    "A clear, concise summary of the review findings (2-3 paragraphs). Highlight the most critical points.\n\n"
                    "## Related Work\n"
                    "A dedicated section listing competing tools, frameworks, and approaches. For each:\n"
                    "- Tool/Framework name\n"
                    "- How it differs from the reviewed paper\n"
                    "- Key strengths and weaknesses compared to the reviewed paper\n"
                    "CRITICAL: Only include papers/tools that were found in the search results. Never fabricate.\n\n"
                    "## Response to Authors\n"
                    "A constructive, professional letter organized by:\n"
                    "1. Major Issues (must address before publication)\n"
                    "2. Missing Related Work (cite specific papers from search results)\n"
                    "3. Minor Issues (should address)\n"
                    "4. Suggestions (optional improvements)\n"
                    "5. Overall Recommendation\n\n"
                    "Maintain academic tone. Be specific — reference paper sections when critiquing."
                ),
            },
        ],
    },
    "proposal-writing": {
        "name": "Proposal Writing Pipeline",
        "stages": [
            {
                "id": "research-landscape",
                "role": AgentRole.RESEARCHER.value,
                "task_template": "Research the landscape for this proposal idea:\n\n{input}\n\nIdentify: research gaps, supporting literature, methodology precedents, competing approaches.",
            },
            {
                "id": "design-methodology",
                "role": AgentRole.RESEARCHER.value,
                "task_template": "Design the methodology for this research:\n\n{input}\n\nProvide: experimental design, sampling strategy, statistical analysis plan, data management plan (FAIR).",
            },
            {
                "id": "write-proposal",
                "role": AgentRole.WRITER.value,
                "task_template": "Write the proposal sections:\n\n{input}\n\nProduce: Specific Aims, Research Plan, Budget Justification. Align with evaluation criteria (Excellence, Impact, Implementation).",
            },
            {
                "id": "create-artifacts",
                "role": AgentRole.RESEARCHER.value,
                "task_template": "Create project management artifacts:\n\n{input}\n\nProduce: WBS, Gantt chart, RACI matrix, risk register, exploitation plan, IP strategy.",
            },
        ],
    },
    "conference-prep": {
        "name": "Conference Preparation",
        "stages": [
            {
                "id": "write-paper",
                "role": AgentRole.WRITER.value,
                "task_template": "Write a conference paper for these findings:\n\n{input}\n\nFollow IMRaD structure. Craft abstract. Format for target venue.",
            },
            {
                "id": "review-draft",
                "role": AgentRole.REVIEWER.value,
                "task_template": "Review this conference paper draft:\n\n{input}\n\nCheck: novelty, rigor, presentation quality, claims-evidence alignment.",
            },
            {
                "id": "create-materials",
                "role": AgentRole.WRITER.value,
                "task_template": "Create presentation materials:\n\n{input}\n\nProduce: slide outline, poster layout, pitch deck structure.",
            },
        ],
    },
    "eu-project": {
        "name": "EU Project Lifecycle",
        "stages": [
            {
                "id": "write-proposal",
                "role": AgentRole.WRITER.value,
                "task_template": "Write the EU Horizon Europe proposal:\n\n{input}\n\nStructure Part B (Excellence, Impact, Implementation). Define WPs, deliverables, milestones.",
            },
            {
                "id": "create-framework",
                "role": AgentRole.RESEARCHER.value,
                "task_template": "Create project management framework:\n\n{input}\n\nProduce: WBS, Gantt, RACI, KPI dashboard, periodic report template, consortium coordination plan.",
            },
            {
                "id": "review-deliverables",
                "role": AgentRole.REVIEWER.value,
                "task_template": "Review deliverables and compliance:\n\n{input}\n\nCheck: EU requirements, exploitation plan quality, dissemination strategy, ethics compliance.",
            },
        ],
    },
}


class WorkflowExecuteRequest(BaseModel):
    workflow_id: str
    input: str | None = None
    paper_id: UUID | None = None
    agent_assignments: dict[str, UUID]


class WorkflowExecuteResponse(BaseModel):
    workflow_id: str
    workflow_name: str
    stages: list[dict]


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


async def _run_stage(db: AsyncSession, user_id: str, stage_def: dict, context: str, config_id: UUID) -> dict:
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
    skill_tools = []
    for s in config.skills:
        skill_tools.extend(s.builtin_tools or [])

    from app.tools import get_tools_by_names
    resolved_tools = get_tools_by_names(list(set(skill_tools)))

    system_prompt = config.system_prompt or ""
    if skill_prompts:
        system_prompt += "\n\nAdditional knowledge:\n" + "\n---\n".join(skill_prompts)

    agent_type = config.role.value if hasattr(config.role, "value") else config.role
    
    agent = create_agent(
        agent_type=agent_type,
        model=config.model,
        provider=config.provider,
        strategy="direct",
        system_prompt=system_prompt,
        tools=resolved_tools,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )

    task = stage_def["task_template"].format(input=context)
    messages = [HumanMessage(content=task)]
    max_retries = 3
    last_error = None
    for attempt in range(max_retries):
        try:
            result = await asyncio.wait_for(agent.run(messages), timeout=STAGE_TIMEOUT_SECONDS)
            return {
                "agent_role": stage_def["role"],
                "agent_name": config.name,
                "status": "completed",
                "output": result.get("output", ""),
                "metadata": result.get("metadata", {}),
            }
        except asyncio.TimeoutError:
            logger.warning(f"Stage for role {stage_def['role']} timed out after {STAGE_TIMEOUT_SECONDS}s")
            return {
                "agent_role": stage_def["role"],
                "agent_name": config.name,
                "status": "timeout",
                "output": f"Stage timed out after {STAGE_TIMEOUT_SECONDS} seconds. Previous stage output preserved.",
                "metadata": {"timeout_seconds": STAGE_TIMEOUT_SECONDS},
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

    logger.error(f"Stage for role {stage_def['role']} failed: {last_error}")
    return {
        "agent_role": stage_def["role"],
        "agent_name": config.name,
        "status": "error",
        "output": f"Stage failed: {type(last_error).__name__}: {str(last_error)[:500]}",
        "metadata": {"error_type": type(last_error).__name__},
    }


async def _fetch_paper_content(db: AsyncSession, user_id: str, paper_id: UUID) -> str:
    result = await db.execute(
        select(Paper).where(Paper.id == paper_id, Paper.owner_id == user_id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    parts = []
    if paper.title:
        parts.append(f"Title: {paper.title}")
    if paper.authors:
        parts.append(f"Authors: {', '.join(paper.authors)}")
    if paper.abstract:
        parts.append(f"Abstract: {paper.abstract}")

    # Include AI-extracted metadata for better search queries
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

    return "\n\n".join(parts)


def _build_stage_context(original_input: str, prior_findings: list[dict]) -> str:
    if not prior_findings:
        return original_input

    budgets = budget_for_stages()
    paper_budget = budgets["paper_content"]
    prior_budget = budgets["prior_stages"]

    paper_fitted = fit_to_budget(original_input, paper_budget, label="paper")

    parts = [f"PAPER / INPUT:\n{paper_fitted}"]
    parts.append("\n--- PRIOR STAGE OUTPUTS ---\n")
    per_stage = max(prior_budget // max(len(prior_findings), 1), 500)
    for finding in prior_findings:
        fitted = fit_to_budget(finding["output"], per_stage, label=f"stage:{finding['stage']}")
        parts.append(f"[Stage: {finding['stage']} | Role: {finding['role']} | Agent: {finding['agent_name']}]\n{fitted}\n")
    return "\n".join(parts)


@router.post("/execute", response_model=WorkflowExecuteResponse)
async def execute_workflow(
    req: WorkflowExecuteRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.workflow_id not in WORKFLOW_DEFINITIONS:
        return WorkflowExecuteResponse(
            workflow_id=req.workflow_id,
            workflow_name="Unknown",
            stages=[{"status": "error", "output": f"Unknown workflow: {req.workflow_id}"}],
        )

    if req.paper_id:
        context = await _fetch_paper_content(db, user_id, req.paper_id)
    elif req.input:
        context = req.input
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either input or paper_id must be provided",
        )

    workflow = WORKFLOW_DEFINITIONS[req.workflow_id]
    stage_results = []
    start_time = time.time()

    original_context = context
    prior_findings = []

    for i, stage_def in enumerate(workflow["stages"]):
        role = stage_def["role"]
        stage_id = stage_def.get("id")
        config_id = req.agent_assignments.get(stage_id)
        if not config_id:
            return WorkflowExecuteResponse(
                workflow_id=req.workflow_id,
                workflow_name=workflow["name"],
                stages=[{"status": "error", "output": f"Missing agent assignment for stage: {stage_id}"}],
            )

        stage_context = _build_stage_context(original_context, prior_findings)

        result = await _run_stage(db, user_id, stage_def, stage_context, config_id)
        stage_results.append(result)

        prev_output = result.get("output", "")
        if prev_output:
            prior_findings.append({
                "stage": stage_def.get("id", f"stage-{i}"),
                "role": role,
                "agent_name": result.get("agent_name", ""),
                "output": prev_output,
            })

        if i < len(workflow["stages"]) - 1:
            await asyncio.sleep(STAGE_DELAY_SECONDS)

    duration = time.time() - start_time
    overall_status = "completed"
    for s in stage_results:
        if s.get("status") in ("timeout", "error"):
            overall_status = "partial"
            break

    execution = WorkflowExecution(
        user_id=user_id,
        workflow_id=req.workflow_id,
        workflow_name=workflow["name"],
        input_text=req.input,
        paper_id=req.paper_id,
        agent_assignments={k: str(v) for k, v in req.agent_assignments.items()},
        stages=stage_results,
        status=overall_status,
        duration_seconds=round(duration, 2),
    )
    db.add(execution)
    await db.commit()

    return WorkflowExecuteResponse(
        workflow_id=req.workflow_id,
        workflow_name=workflow["name"],
        stages=stage_results,
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
    await db.delete(execution)
    await db.commit()
    return {"status": "deleted", "id": str(execution_id)}


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
    for e in executions:
        await db.delete(e)
    await db.commit()
    return {"status": "deleted", "count": count}
