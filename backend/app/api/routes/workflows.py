import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from langchain_core.messages import HumanMessage
import io

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import AgentConfig, Paper, PaperChunk, AgentRole, WorkflowExecution
from app.agents.factory import create_agent
from app.utils.context_budget import fit_to_budget, budget_for_stages
from app.utils.pdf_model_support import model_supports_pdf, create_multimodal_human_message

STAGE_TIMEOUT_SECONDS = 300.0
STAGE_DELAY_SECONDS = 15

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
                "id": "refine-review",
                "role": AgentRole.WRITER.value,
                "task_template": (
                    "You are an Academic Writer. Transform the raw review below into a polished, professional peer review.\n\n"
                    "Review to refine:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce a polished document with these exact sections using professional academic markdown:\n\n"
                    "## Reviewer Summary\n"
                    "A clear, concise summary of the review findings (2-3 paragraphs). Highlight the most critical points "
                    "and the overall recommendation. Use bold for key findings.\n\n"
                    "## Related Work Analysis\n"
                    "Present as a table with columns: Category, Tool/Work, Key Contribution, "
                    "Strengths vs Reviewed Paper, Weaknesses vs Reviewed Paper\n"
                    "Group by category (e.g., DSL-based approaches, ML frameworks, formal methods). "
                    "CRITICAL: Only include papers/tools found in the search results. Never fabricate.\n\n"
                    "## Response to Authors\n"
                    "A professional letter organized by priority:\n\n"
                    "### 1. Major Issues\n"
                    "Issues that must be addressed before publication. Reference specific sections from the paper.\n\n"
                    "### 2. Missing Related Work\n"
                    "Cite specific papers from the search results. Explain how they are relevant and what the authors should add.\n\n"
                    "### 3. Minor Issues\n"
                    "Additional concerns that should be addressed.\n\n"
                    "### 4. Suggestions\n"
                    "Optional improvements for strengthening the work.\n\n"
                    "### 5. Recommendation\n"
                    "**Decision**: Accept / Minor Revision / Major Revision / Reject\n"
                    "Include a 1-2 sentence justification for the decision.\n\n"
                    "IMPORTANT: Maintain academic tone throughout. Be specific — reference paper sections when critiquing. "
                    "Use tables where data comparison is needed. This output will appear in a professional PDF report."
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
                "task_template": (
                    "You are a Research Analyst mapping the landscape for a research proposal.\n\n"
                    "Proposal idea:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce a structured landscape analysis using professional academic markdown:\n\n"
                    "## Research Context\n"
                    "Brief overview of the research area and why this proposal is timely. (1-2 paragraphs)\n\n"
                    "## Research Gaps Identified\n"
                    "Table with columns: Gap, Importance, Current Limitations, How This Proposal Addresses It\n"
                    "Identify at least 3-5 distinct research gaps.\n\n"
                    "## Supporting Literature\n"
                    "Table with columns: #, Key Work, Authors, Year, Key Findings, Relevance to Proposal\n"
                    "Include 8-12 key papers that support the proposal's rationale.\n\n"
                    "## Methodology Precedents\n"
                    "Table with columns: Methodology/Approach, Used In, Strengths, Weaknesses, Applicability to This Proposal\n\n"
                    "## Competing Approaches\n"
                    "Table with columns: Approach/Framework, Research Group, Key Differentiator, Why This Proposal is Distinct\n\n"
                    "## Gap Analysis Summary\n"
                    "A paragraph synthesizing the landscape and explicitly stating the niche this proposal occupies."
                ),
            },
            {
                "id": "design-methodology",
                "role": AgentRole.RESEARCHER.value,
                "task_template": (
                    "You are a Research Methodologist designing the methodology for a research proposal.\n\n"
                    "Proposal context:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce a methodology design using professional academic markdown:\n\n"
                    "## Research Questions / Hypotheses\n"
                    "Clearly stated research questions or hypotheses that the methodology will address.\n\n"
                    "## Experimental Design\n"
                    "### Study Design\n"
                    "Describe the overall design (e.g., controlled experiment, case study, longitudinal study).\n"
                    "### Variables\n"
                    "Table with columns: Variable, Type (Independent/Dependent/Controlled), Operational Definition, Measurement\n"
                    "### Groups / Conditions\n"
                    "Describe experimental and control conditions.\n"
                    "### Procedure\n"
                    "Step-by-step procedure in numbered list.\n\n"
                    "## Sampling Strategy\n"
                    "### Population\n"
                    "### Sample Size Justification\n"
                    "### Sampling Method\n\n"
                    "## Statistical Analysis Plan\n"
                    "Table with columns: Research Question, Data Type, Statistical Test, Justification\n\n"
                    "## Data Management Plan\n"
                    "### Data Collection\n"
                    "### Data Storage and Security\n"
                    "### FAIR Principles Compliance\n"
                    "Table with columns: FAIR Principle, Implementation Strategy, Timeline\n"
                    "### Data Sharing and Preservation\n\n"
                    "## Limitations and Mitigations\n"
                    "Table with columns: Limitation, Impact, Mitigation Strategy\n\n"
                    "IMPORTANT: Be specific and detailed. Use tables for structured comparisons."
                ),
            },
            {
                "id": "write-proposal",
                "role": AgentRole.WRITER.value,
                "task_template": (
                    "You are a Grant Proposal Writer crafting a compelling research proposal.\n\n"
                    "Proposal context:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce proposal sections using professional academic markdown:\n\n"
                    "## Specific Aims\n"
                    "### Overall Goal\n"
                    "Single sentence stating the long-term goal.\n"
                    "### Specific Aim 1\n"
                    "Hypothesis, rationale, approach, expected outcomes, success criteria.\n"
                    "### Specific Aim 2\n"
                    "Same structure.\n"
                    "### Specific Aim 3 (optional)\n"
                    "Same structure.\n"
                    "### Impact Statement\n"
                    "How achieving these aims will advance the field.\n\n"
                    "## Research Plan\n"
                    "Organized by aims. For each aim:\n"
                    "### Approach\n"
                    "### Preliminary Studies / Proof of Concept\n"
                    "### Expected Results\n"
                    "### Potential Pitfalls and Alternatives\n\n"
                    "## Budget Justification\n"
                    "Table with columns: Category, Item, Cost, Justification\n"
                    "Categories: Personnel, Equipment, Travel, Materials and Supplies, Publication Costs, Other\n\n"
                    "## Alignment with Evaluation Criteria\n"
                    "### Excellence\n"
                    "How the proposal demonstrates novelty, ambition, and soundness.\n"
                    "### Impact\n"
                    "Expected scientific, economic, and societal impacts.\n"
                    "### Implementation\n"
                    "Feasibility, project plan, consortium capability.\n\n"
                    "IMPORTANT: Write persuasively. Use bold for key claims. Use tables for budget and timeline."
                ),
            },
            {
                "id": "create-artifacts",
                "role": AgentRole.RESEARCHER.value,
                "task_template": (
                    "You are a Project Manager creating project management artifacts for a research proposal.\n\n"
                    "Proposal context:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce artifacts using professional markdown with tables:\n\n"
                    "## Work Breakdown Structure\n"
                    "### Work Package 1: [Name]\n"
                    "- Leader: [Role]\n"
                    "- Objectives: ...\n"
                    "- Tasks: [Numbered list]\n"
                    "- Deliverables: [List with months]\n"
                    "- Person-months: [Count]\n"
                    "### Work Package 2: [Name]\n"
                    "...\n"
                    "(Include 4-8 work packages total)\n\n"
                    "## Gantt Chart (Textual Representation)\n"
                    "Table with columns: WP, Task, M1-M3, M4-M6, M7-M9, M10-M12, M13-M18, M19-M24, M25-M36\n"
                    "Mark cells with X for active periods.\n\n"
                    "## RACI Matrix\n"
                    "Table with columns: Task, PI, Co-PI, Researcher A, Researcher B, Postdoc, External Partner\n"
                    "Mark cells with R (Responsible), A (Accountable), C (Consulted), I (Informed).\n\n"
                    "## Risk Register\n"
                    "Table with columns: Risk, Probability (H/M/L), Impact (H/M/L), Mitigation Strategy, Contingency Plan, Owner\n\n"
                    "## Exploitation Plan\n"
                    "Table with columns: Result, Type (IP/Know-how/Data/Software), Protection Strategy, Target Users, Timeline\n\n"
                    "## IP Strategy\n"
                    "### Background IP\n"
                    "### Foreground IP\n"
                    "### Ownership and Access Rights\n\n"
                    "IMPORTANT: Be comprehensive and realistic. Use tables extensively."
                ),
            },
        ],
    },
    "conference-prep": {
        "name": "Conference Preparation",
        "stages": [
            {
                "id": "write-paper",
                "role": AgentRole.WRITER.value,
                "task_template": (
                    "You are an Academic Paper Writer preparing a conference paper.\n\n"
                    "Research findings:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce a conference paper using professional academic markdown:\n\n"
                    "## Title\n"
                    "A compelling, descriptive title.\n\n"
                    "## Authors and Affiliations\n"
                    "Placeholder format.\n\n"
                    "## Abstract\n"
                    "150-250 words covering: Background, Problem, Method, Results, Contribution.\n\n"
                    "## Keywords\n"
                    "4-6 keywords.\n\n"
                    "## IMRaD Structure\n"
                    "### Introduction\n"
                    "Problem statement, motivation, related work summary, research gap, contribution statement.\n"
                    "### Methods\n"
                    "Detailed methodology with appropriate subsections.\n"
                    "### Results\n"
                    "Present findings with tables and structured descriptions.\n"
                    "### Discussion\n"
                    "Interpretation of results, limitations, comparison with prior work.\n"
                    "### Conclusion\n"
                    "Summary of contributions and future work.\n\n"
                    "## References\n"
                    "List of 15-25 references in the venue's format style.\n\n"
                    "IMPORTANT: Follow IMRaD structure rigorously. Use clear section headers. "
                    "Include placeholder figures/tables with captions. Format for a top-tier conference."
                ),
            },
            {
                "id": "review-draft",
                "role": AgentRole.REVIEWER.value,
                "task_template": (
                    "You are a Conference Reviewer evaluating a paper draft.\n\n"
                    "Paper:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce a structured review using professional markdown:\n\n"
                    "## Summary\n"
                    "1-2 paragraph summary of the paper.\n\n"
                    "## Novelty Assessment\n"
                    "**Rating**: [High/Moderate/Low]\n"
                    "Justification of the novelty rating.\n\n"
                    "## Rigor Evaluation\n"
                    "**Rating**: [High/Moderate/Low]\n"
                    "Check: methodology soundness, experimental design, statistical analysis.\n\n"
                    "## Presentation Quality\n"
                    "**Rating**: [High/Moderate/Low]\n"
                    "Check: clarity, organization, figure quality, writing quality.\n\n"
                    "## Claims-Evidence Alignment\n"
                    "Table with columns: Claim, Location, Evidence Provided, Alignment (Strong/Partial/Weak), Gap\n\n"
                    "## Strengths\n"
                    "Numbered list.\n\n"
                    "## Weaknesses\n"
                    "Numbered list.\n\n"
                    "## Questions for Authors\n"
                    "Numbered list of specific questions.\n\n"
                    "## Recommendation\n"
                    "**Decision**: Accept / Weak Accept / Borderline / Weak Reject / Reject\n"
                    "Brief justification for the recommendation.\n\n"
                    "IMPORTANT: Be constructive and specific. Reference line numbers or sections where relevant."
                ),
            },
            {
                "id": "create-materials",
                "role": AgentRole.WRITER.value,
                "task_template": (
                    "You are a Conference Presentation Designer creating presentation materials.\n\n"
                    "Paper/presentation content:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce materials using professional markdown:\n\n"
                    "## Slide Deck Outline\n"
                    "Table with columns: Slide #, Title, Key Content, Visual Elements, Duration (min)\n"
                    "Include 10-15 slides covering the full presentation arc.\n\n"
                    "## Poster Layout\n"
                    "### Sections\n"
                    "Table with columns: Section, Content Summary, Recommended Size (%), Key Visuals\n"
                    "### Design Recommendations\n"
                    "Color scheme, font sizes, figure placement, QR code for supplementary materials.\n\n"
                    "## Pitch Deck Structure\n"
                    "### Elevator Pitch (30 seconds)\n"
                    "### Full Pitch (3 minutes)\n"
                    "Flip through key slides with timing annotations.\n\n"
                    "## Audience Q&A Preparation\n"
                    "### Anticipated Questions\n"
                    "Table with columns: Question, Suggested Response\n"
                    "Include 5-8 likely questions.\n\n"
                    "IMPORTANT: Be practical and actionable. A researcher should be able to create slides directly from this outline."
                ),
            },
        ],
    },
    "eu-project": {
        "name": "EU Project Lifecycle",
        "stages": [
            {
                "id": "write-proposal",
                "role": AgentRole.WRITER.value,
                "task_template": (
                    "You are an EU Horizon Europe Proposal Writer preparing a competitive proposal.\n\n"
                    "Proposal context:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce a structured proposal section using professional academic markdown:\n\n"
                    "## Excellence\n"
                    "### Objectives\n"
                    "Clear, measurable objectives aligned with the Work Programme topic.\n"
                    "### Concept and Approach\n"
                    "Overall concept, underlying ideas, approaches used.\n"
                    "### Ambition\n"
                    "Beyond state of the art, novelty, and innovation potential.\n\n"
                    "## Impact\n"
                    "### Expected Impacts\n"
                    "Table with columns: Expected Impact, Target Group, Measurement Indicator, Timeline\n"
                    "### Dissemination and Exploitation\n"
                    "Plan for disseminating results (publications, conferences, open science).\n"
                    "### Communication Activities\n"
                    "Public engagement and outreach activities.\n\n"
                    "## Implementation\n"
                    "### Work Plan\n"
                    "Table with columns: WP, Title, Lead, Start Month, End Month, Effort (PM)\n"
                    "Include 6-10 work packages.\n"
                    "### Deliverables\n"
                    "Table with columns: D#, Deliverable Name, WP, Type (R/DEM/DEC/OTHER), Dissemination Level (PU/SEN/CI), Due Month\n"
                    "### Milestones\n"
                    "Table with columns: M#, Milestone Name, WP, Means of Verification, Due Month\n"
                    "### Consortium Capacity\n"
                    "Description of partner expertise and complementarity.\n"
                    "### Resources\n"
                    "Table with columns: Partner, Role, Key Expertise, Effort (PM), Budget (EUR)\n\n"
                    "## Ethics and Security\n"
                    "### Ethics Compliance\n"
                    "Identify ethics issues and how they will be addressed.\n"
                    "### Security Considerations\n\n"
                    "IMPORTANT: Follow Horizon Europe proposal structure. Use tables extensively. "
                    "Be specific with numbers, timelines, and measurable outcomes."
                ),
            },
            {
                "id": "create-framework",
                "role": AgentRole.RESEARCHER.value,
                "task_template": (
                    "You are a Project Manager creating management frameworks for an EU Horizon Europe project.\n\n"
                    "Project context:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce management artifacts using professional markdown:\n\n"
                    "## Work Breakdown Structure\n"
                    "Detailed WBS with WPs, tasks, sub-tasks, deliverables, and responsible partners.\n"
                    "Table with columns: WP, Task, Lead, Effort (PM), Deliverable, Due Month\n\n"
                    "## Gantt Chart (Textual)\n"
                    "Table with months/years across the project duration (typically 36-48 months).\n"
                    "Rows: WPs and key tasks. Mark active periods.\n\n"
                    "## RACI Matrix\n"
                    "Table with columns: Task/Decision, Coordinator, WP Lead, Partners, Advisory Board\n\n"
                    "## KPI Dashboard\n"
                    "Table with columns: KPI, Target Value, Measurement Method, Frequency, Responsible\n"
                    "Cover: scientific, dissemination, management, impact KPIs.\n\n"
                    "## Periodic Report Template\n"
                    "### Reporting Period Structure\n"
                    "### Section Outline\n"
                    "- Project objectives and progress\n"
                    "- Work package progress (per WP)\n"
                    "- Deliverables submitted\n"
                    "- Milestones achieved\n"
                    "- Deviations and corrective actions\n"
                    "- Dissemination and exploitation updates\n"
                    "- Financial summary\n\n"
                    "## Consortium Coordination Plan\n"
                    "### Governance Structure\n"
                    "### Communication Plan\n"
                    "### Decision-Making Process\n"
                    "### Conflict Resolution Mechanism\n"
                    "### Quality Assurance Process\n\n"
                    "IMPORTANT: Be comprehensive. These artifacts will be used in a real EU project management context."
                ),
            },
            {
                "id": "review-deliverables",
                "role": AgentRole.REVIEWER.value,
                "task_template": (
                    "You are an EU Project Reviewer evaluating deliverables and compliance.\n\n"
                    "Project context:\n{input}\n\n"
                    "OUTPUT FORMAT — Produce a compliance review using professional markdown:\n\n"
                    "## Executive Summary\n"
                    "Overall assessment of compliance status. (1-2 paragraphs)\n\n"
                    "## EU Requirements Compliance\n"
                    "Table with columns: Requirement, Status (Compliant/Partial/Non-compliant), Evidence, Remediation Needed\n"
                    "Cover: Grant Agreement terms, Work Programme alignment, reporting obligations.\n\n"
                    "## Exploitation Plan Assessment\n"
                    "**Quality Rating**: [Excellent/Good/Adequate/Poor]\n"
                    "### Strengths\n"
                    "### Weaknesses\n"
                    "### Recommendations\n"
                    "### TRL Assessment\n"
                    "Current TRL, target TRL, plan credibility.\n\n"
                    "## Dissemination Strategy Assessment\n"
                    "**Quality Rating**: [Excellent/Good/Adequate/Poor]\n"
                    "### Target Audiences\n"
                    "Table with columns: Audience, Dissemination Channel, Timing, Success Measure\n"
                    "### Open Science Compliance\n"
                    "Open access publishing, data sharing, FAIR principles.\n\n"
                    "## Ethics Compliance\n"
                    "Table with columns: Ethics Issue, How Addressed, Status, Reviewer Notes\n"
                    "Cover: human participants, data protection, animal research, dual use, etc.\n\n"
                    "## Risk Assessment\n"
                    "Table with columns: Risk Category, Risk Description, Probability (H/M/L), Impact (H/M/L), Mitigation Adequacy\n\n"
                    "## Overall Rating\n"
                    "**Pass / Conditional Pass / Fail**\n"
                    "Include summary justification and required actions for conditional pass.\n\n"
                    "IMPORTANT: Be thorough and constructive. Reference specific EU requirements and guidelines."
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


async def _run_stage(
    db: AsyncSession,
    user_id: str,
    stage_def: dict,
    context: str,
    config_id: UUID,
    pdf_bytes: Optional[bytes] = None,
    paper_s2_id: str | None = None,
    topic_query: str | None = None,
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

    max_retries = 3
    last_error = None
    for attempt in range(max_retries):
        try:
            result = await asyncio.wait_for(agent.run(messages, context=agent_context), timeout=STAGE_TIMEOUT_SECONDS)
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


async def _fetch_paper_content(db: AsyncSession, user_id: str, paper_id: UUID) -> PaperContent:
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

    text = "\n\n".join(parts)

    pdf_bytes: Optional[bytes] = None
    if paper.minio_key:
        try:
            from app.services.minio_service import minio_service
            pdf_bytes = await minio_service.download_file(paper.minio_key)
        except Exception as e:
            logger.warning(f"Failed to download PDF from MinIO for paper {paper_id}: {e}")

    return PaperContent(text=text, pdf_bytes=pdf_bytes)


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

    paper_content: Optional[PaperContent] = None
    pdf_bytes: Optional[bytes] = None
    paper_s2_id: Optional[str] = None
    topic_query: Optional[str] = None
    if req.paper_id:
        paper_content = await _fetch_paper_content(db, user_id, req.paper_id)
        context = paper_content.text
        pdf_bytes = paper_content.pdf_bytes

        if req.input:
            context = f"{context}\n\n## Custom Instructions\n{req.input}"

        # Resolve S2 paper ID from DOI or arXiv ID for related work search
        paper_result = await db.execute(
            select(Paper).where(Paper.id == req.paper_id, Paper.owner_id == user_id)
        )
        paper = paper_result.scalar_one_or_none()
        if paper:
            if paper.doi:
                paper_s2_id = f"DOI:{paper.doi}"
            elif paper.arxiv_id:
                paper_s2_id = f"ARXIV:{paper.arxiv_id}"
            # Build topic query from title + keywords for fallback search
            parts = []
            if paper.title:
                parts.append(paper.title)
            if paper.analysis and paper.analysis.get("keywords"):
                parts.extend(paper.analysis["keywords"][:3])
            topic_query = " ".join(parts) if parts else None
    elif req.input:
        context = req.input
        topic_query = req.input[:200] if len(req.input) > 200 else req.input
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

        result = await _run_stage(
            db, user_id, stage_def, stage_context, config_id,
            pdf_bytes=pdf_bytes, paper_s2_id=paper_s2_id, topic_query=topic_query,
        )
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

            output = stage.get("output", "")
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
        import pymupdf
        import markdown as md_lib
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF generation library not available",
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

    doc = pymupdf.open()
    story = pymupdf.Story(html=full_html)

    while True:
        page = doc.new_page()
        more, _ = story.place(page.rect)
        story.draw(page)
        if not more:
            break

    pdf_bytes = doc.tobytes()
    doc.close()

    filename = f"{execution.workflow_name.lower().replace(' ', '_')}_{execution.id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
