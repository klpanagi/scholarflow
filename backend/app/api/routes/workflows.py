import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from langchain_core.messages import HumanMessage

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, AgentConfig, Paper, PaperChunk, AgentRole
from app.agents.factory import create_agent

STAGE_TIMEOUT_SECONDS = 90.0

logger = logging.getLogger(__name__)

router = APIRouter()


WORKFLOW_DEFINITIONS = {
    "paper-review": {
        "name": "Paper Review Pipeline",
        "stages": [
            {
                "id": "search-related-work",
                "role": AgentRole.RESEARCHER.value,
                "task_template": "Search for related work and verify citations for this paper:\n\n{input}\n\nReturn: list of related papers, citation verification results, novelty assessment.",
            },
            {
                "id": "review-paper",
                "role": AgentRole.REVIEWER.value,
                "task_template": "Review this paper using your pipeline:\n\n{input}\n\nExecute: intake, claims extraction, synthesis. Produce a single consolidated review with actionable feedback organized by priority.",
            },
            {
                "id": "refine-review",
                "role": AgentRole.WRITER.value,
                "task_template": "Refine this review into constructive author feedback:\n\n{input}\n\nProduce a polished review with actionable suggestions organized by priority.",
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
            t = s.prompt_template
            if len(t) > 600:
                t = t[:600] + "\n[... truncated ...]"
            skill_prompts.append(t)
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
        parts.append(f"Abstract: {paper.abstract[:1500]}")
    return "\n\n".join(parts)


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
            
        result = await _run_stage(db, user_id, stage_def, context, config_id)
        stage_results.append(result)
        if i < len(workflow["stages"]) - 1:
            prev_output = result.get("output", "")
            if len(prev_output) > 4000:
                prev_output = prev_output[:4000] + "\n\n[... output truncated for next stage ...]"
            context = prev_output

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
