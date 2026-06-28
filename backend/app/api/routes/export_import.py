from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import AgentConfig, Skill
from app.schemas import AgentConfigExport, ExportBundle, SkillExport

router = APIRouter()


@router.get("/export")
async def export_skills_and_agents(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExportBundle:
    """Export the authenticated user's skills and agent configurations."""
    skills_result = await db.execute(
        select(Skill).where(Skill.user_id == user_id)
    )
    skills = skills_result.scalars().all()

    agents_result = await db.execute(
        select(AgentConfig)
        .where(AgentConfig.user_id == user_id)
        .options(selectinload(AgentConfig.skills))
    )
    agents = agents_result.scalars().all()

    skill_exports = [
        SkillExport(
            name=s.name,
            description=s.description,
            prompt_template=s.prompt_template,
            builtin_tools=s.builtin_tools or [],
            custom_tools=s.custom_tools or [],
            input_schema=s.input_schema,
            output_schema=s.output_schema,
            tags=s.tags or [],
            is_public=s.is_public,
        )
        for s in skills
    ]

    agent_exports = [
        AgentConfigExport(
            name=a.name,
            role=a.role.value if hasattr(a.role, "value") else a.role,
            provider=a.provider,
            model=a.model,
            temperature=a.temperature,
            max_tokens=a.max_tokens,
            strategy=a.strategy.value if hasattr(a.strategy, "value") else a.strategy,
            tools=a.tools or [],
            system_prompt=a.system_prompt,
            is_default=a.is_default,
            variant=a.variant.value if a.variant and hasattr(a.variant, "value") else a.variant,
            skill_names=[s.name for s in (a.skills or [])],
        )
        for a in agents
    ]

    return ExportBundle(
        version=1,
        format="academic-pal-skills-agents-v1",
        exported_at=datetime.now(timezone.utc).isoformat(),
        skills=skill_exports,
        agent_configs=agent_exports,
    )
