import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import AgentConfig, Skill, User, agent_skills_table
from app.schemas import (
    AgentConfigUpdateWithSkills,
    SkillCreate,
    SkillResponse,
    SkillUpdate,
)

router = APIRouter()


async def _get_user(user_id: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


BUILTIN_TOOLS = [
    {"name": "search_papers", "description": "Search academic papers across Semantic Scholar, arXiv, and CrossRef"},
    {"name": "search_web", "description": "Search the web for supplementary information"},
    {"name": "extract_pdf_text", "description": "Extract text content from a PDF stored in MinIO"},
    {"name": "extract_citations", "description": "Extract citations from a PDF stored in MinIO"},
    {"name": "format_citation", "description": "Format a citation in APA, MLA, Chicago, or IEEE style"},
    {"name": "find_citation", "description": "Find a paper and return its citation metadata"},
    {"name": "read_document", "description": "Extract text from PDF, DOCX, XLSX, PPTX, HTML, or text files"},
]


@router.get("/builtin-tools")
async def list_builtin_tools(user_id: str = Depends(get_current_user)):
    return BUILTIN_TOOLS


@router.post("/", response_model=SkillResponse)
async def create_skill(
    data: SkillCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user(user_id, db)
    skill = Skill(
        user_id=user_id,
        name=data.name,
        description=data.description,
        prompt_template=data.prompt_template,
        builtin_tools=data.builtin_tools,
        custom_tools=[t.model_dump() for t in data.custom_tools] if data.custom_tools else [],
        input_schema=data.input_schema,
        output_schema=data.output_schema,
        tags=data.tags,
        is_public=data.is_public,
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill


@router.get("/", response_model=list[SkillResponse])
async def list_skills(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Skill).where((Skill.user_id == user_id) | (Skill.is_public == True))
    )
    skills = result.scalars().all()
    # Deduplicate by name. Seed skills are copied per user with is_public=True,
    # so the (user_id | is_public) query returns N copies of each seed. Prefer the
    # current user's own skill so they always see their own editable version.
    # Cast the column to str for type checkers that don't follow SQLAlchemy's
    # descriptor protocol. At runtime skill.name is already a str.
    user_id_str = str(user_id)
    by_name: dict[str, Skill] = {}
    for skill in skills:
        name: str = str(skill.name)
        existing = by_name.get(name)
        if existing is None or (str(existing.user_id) != user_id_str and str(skill.user_id) == user_id_str):
            by_name[name] = skill
    return list(by_name.values())

@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.patch("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: uuid.UUID,
    data: SkillUpdate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    update_data = data.model_dump(exclude_unset=True)
    if "custom_tools" in update_data and update_data["custom_tools"] is not None:
        update_data["custom_tools"] = [
            t.model_dump() if hasattr(t, "model_dump") else t
            for t in update_data["custom_tools"]
        ]
    for key, value in update_data.items():
        setattr(skill, key, value)
    await db.commit()
    await db.refresh(skill)
    return skill


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    await db.delete(skill)
    await db.commit()
    return {"status": "deleted"}


@router.post("/assign/{config_id}")
async def assign_skills_to_agent(
    config_id: uuid.UUID,
    data: AgentConfigUpdateWithSkills,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentConfig)
        .options(selectinload(AgentConfig.skills))
        .where(AgentConfig.id == config_id, AgentConfig.user_id == user_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Agent config not found")

    skills_result = await db.execute(
        select(Skill).where(Skill.id.in_(data.skill_ids))
    )
    skills = skills_result.scalars().all()
    config.skills = list(skills)
    await db.commit()
    await db.refresh(config)
    return {"status": "updated", "skill_count": len(config.skills)}
