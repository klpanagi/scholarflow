from __future__ import annotations

import uuid as uuid_module
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import (
    AgentConfig,
    AgentRole,
    AgentVariant,
    Skill,
    Strategy,
    agent_skills_table,
)
from app.schemas import (
    AgentConfigExport,
    ExportBundle,
    ImportConflict,
    ImportConfirmRequest,
    ImportDecision,
    ImportPreview,
    ImportResult,
    SkillExport,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory staging store (30-min TTL)
# ---------------------------------------------------------------------------


@dataclass
class StagingData:
    bundle: dict
    conflicts: list[dict]
    consumed: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_staging_store: dict[str, StagingData] = {}
_STAGING_TTL = timedelta(minutes=30)


def _clean_expired_staging() -> None:
    now = datetime.now(timezone.utc)
    expired = [
        k for k, v in _staging_store.items() if now - v.created_at > _STAGING_TTL
    ]
    for k in expired:
        del _staging_store[k]


def _get_differences(existing, incoming) -> list[str]:
    """Compare an existing DB model with an incoming Pydantic schema.

    Returns a list of field names that differ between the two.
    """
    diffs: list[str] = []
    incoming_dict = (
        incoming.model_dump() if hasattr(incoming, "model_dump") else incoming
    )

    for key in incoming_dict:
        if key == "name":
            continue

        e_val = getattr(existing, key, None)
        i_val = incoming_dict[key]

        # Handle SQLAlchemy enum types
        e_val = getattr(e_val, "value", e_val)

        # Normalise None / empty-list equivalence
        if e_val is None and isinstance(i_val, list) and len(i_val) == 0:
            continue
        if i_val is None and isinstance(e_val, list) and len(e_val) == 0:
            continue

        if str(e_val) != str(i_val):
            diffs.append(key)

    return diffs


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


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


@router.post("/import")
async def import_staging(
    bundle: ExportBundle,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImportPreview:
    """Stage an import bundle, validate structure and detect conflicts.

    Returns an ``ImportPreview`` with a ``staging_token`` that can be used
    by ``POST /api/import/confirm`` to apply the import.
    """
    _clean_expired_staging()

    # --- version check -------------------------------------------------------
    if bundle.version != 1:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported version: {bundle.version}. Must be 1.",
        )

    # --- duplicate names within bundle ---------------------------------------
    skill_names = [s.name for s in bundle.skills]
    if len(skill_names) != len(set(skill_names)):
        raise HTTPException(
            status_code=422,
            detail="Duplicate skill names in bundle.",
        )

    agent_names = [a.name for a in bundle.agent_configs]
    if len(agent_names) != len(set(agent_names)):
        raise HTTPException(
            status_code=422,
            detail="Duplicate agent config names in bundle.",
        )

    # --- referenced skill names exist ----------------------------------------
    bundle_skill_names = set(skill_names)
    existing_skills_result = await db.execute(
        select(Skill.name).where(Skill.user_id == user_id)
    )
    existing_skill_names = {row[0] for row in existing_skills_result}
    all_known_skill_names = bundle_skill_names | existing_skill_names

    for agent in bundle.agent_configs:
        for ref in agent.skill_names:
            if ref not in all_known_skill_names:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Agent '{agent.name}' references skill '{ref}' "
                        "which is not in the bundle or your existing skills."
                    ),
                )

    # --- conflict detection ---------------------------------------------------
    conflicts: list[ImportConflict] = []

    for s in bundle.skills:
        result = await db.execute(
            select(Skill).where(Skill.user_id == user_id, Skill.name == s.name)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            conflicts.append(
                ImportConflict(
                    conflict_id=str(uuid_module.uuid4()),
                    type="skill",
                    name=s.name,
                    existing={
                        "name": existing.name,
                        "description": existing.description,
                        "prompt_template": existing.prompt_template,
                    },
                    incoming={
                        "name": s.name,
                        "description": s.description,
                        "prompt_template": s.prompt_template,
                    },
                    differences=_get_differences(existing, s),
                )
            )

    for a in bundle.agent_configs:
        result = await db.execute(
            select(AgentConfig).where(
                AgentConfig.user_id == user_id, AgentConfig.name == a.name
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing_role = (
                existing.role.value
                if hasattr(existing.role, "value")
                else existing.role
            )
            conflicts.append(
                ImportConflict(
                    conflict_id=str(uuid_module.uuid4()),
                    type="agent_config",
                    name=a.name,
                    existing={
                        "name": existing.name,
                        "role": existing_role,
                        "model": existing.model,
                    },
                    incoming={
                        "name": a.name,
                        "role": a.role,
                        "model": a.model,
                    },
                    differences=_get_differences(existing, a),
                )
            )

    # --- summary --------------------------------------------------------------
    new_skills = len(bundle.skills) - sum(
        1 for c in conflicts if c.type == "skill"
    )
    new_agents = len(bundle.agent_configs) - sum(
        1 for c in conflicts if c.type == "agent_config"
    )

    summary = {
        "skills": {
            "new": new_skills,
            "conflicts": sum(1 for c in conflicts if c.type == "skill"),
        },
        "agent_configs": {
            "new": new_agents,
            "conflicts": sum(1 for c in conflicts if c.type == "agent_config"),
        },
    }

    # --- persist staging -----------------------------------------------------
    staging_token = str(uuid_module.uuid4())
    _staging_store[staging_token] = StagingData(
        bundle=bundle.model_dump(mode="json"),
        conflicts=[c.model_dump() for c in conflicts],
    )

    return ImportPreview(
        staging_token=staging_token,
        summary=summary,
        conflicts=conflicts,
    )


@router.post("/import/confirm", status_code=201)
async def import_confirm(
    request: ImportConfirmRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImportResult:
    """Apply a staged import, creating/updating skills and agent configs.

    Uses the ``staging_token`` returned by ``POST /api/import`` and applies
    the user's decisions for each conflict.  The entire operation is wrapped
    in a single database transaction.
    """
    _clean_expired_staging()

    # --- validate staging token ----------------------------------------------
    staging = _staging_store.get(request.staging_token)
    if staging is None:
        raise HTTPException(
            status_code=404,
            detail="Staging token not found or expired.",
        )
    if staging.consumed:
        raise HTTPException(
            status_code=409,
            detail="Staging token has already been consumed.",
        )

    # --- build conflict_id → (type, name) mapping ---------------------------
    conflict_map: dict[str, tuple[str, str]] = {}
    for c in staging.conflicts:
        conflict_map[c["conflict_id"]] = (c["type"], c["name"])

    decision_map: dict[str, str] = {
        d.conflict_id: d.action for d in request.decisions
    }

    bundle_data = staging.bundle
    skills_data = bundle_data.get("skills", [])
    agents_data = bundle_data.get("agent_configs", [])

    skills_created = 0
    skills_updated = 0
    skills_skipped = 0
    agents_created = 0
    agents_updated = 0
    agents_skipped = 0
    links_created = 0

    try:
        # ----------------------------------------------------------------
        # Step 1 — Process skills
        # ----------------------------------------------------------------
        for s_data in skills_data:
            name: str = s_data["name"]

            # Find the conflict_id for this skill name (if any)
            conflict_id: str | None = None
            for cid, (ctype, cname) in conflict_map.items():
                if ctype == "skill" and cname == name:
                    conflict_id = cid
                    break

            result = await db.execute(
                select(Skill).where(
                    Skill.user_id == user_id, Skill.name == name
                )
            )
            existing = result.scalar_one_or_none()

            if existing is not None:
                if (
                    conflict_id is not None
                    and decision_map.get(conflict_id) == "overwrite"
                ):
                    existing.description = s_data.get("description")
                    existing.prompt_template = s_data.get("prompt_template")
                    existing.builtin_tools = s_data.get("builtin_tools", []) or []
                    existing.custom_tools = s_data.get("custom_tools") or []
                    existing.input_schema = s_data.get("input_schema")
                    existing.output_schema = s_data.get("output_schema")
                    existing.tags = s_data.get("tags", []) or []
                    existing.is_public = s_data.get("is_public", False)
                    skills_updated += 1
                else:
                    skills_skipped += 1
            else:
                skill = Skill(
                    user_id=user_id,
                    name=name,
                    description=s_data.get("description"),
                    prompt_template=s_data.get("prompt_template"),
                    builtin_tools=s_data.get("builtin_tools", []) or [],
                    custom_tools=s_data.get("custom_tools") or [],
                    input_schema=s_data.get("input_schema"),
                    output_schema=s_data.get("output_schema"),
                    tags=s_data.get("tags", []) or [],
                    is_public=s_data.get("is_public", False),
                )
                db.add(skill)
                skills_created += 1

        # ----------------------------------------------------------------
        # Step 2 — Process agent configs
        # ----------------------------------------------------------------
        for a_data in agents_data:
            name: str = a_data["name"]

            conflict_id: str | None = None
            for cid, (ctype, cname) in conflict_map.items():
                if ctype == "agent_config" and cname == name:
                    conflict_id = cid
                    break

            result = await db.execute(
                select(AgentConfig).where(
                    AgentConfig.user_id == user_id, AgentConfig.name == name
                )
            )
            existing = result.scalar_one_or_none()

            if existing is not None:
                if (
                    conflict_id is not None
                    and decision_map.get(conflict_id) == "overwrite"
                ):
                    existing.role = AgentRole(a_data.get("role", "researcher"))
                    existing.provider = a_data.get("provider", "opencode")
                    existing.model = a_data.get("model", "gpt-4o")
                    existing.temperature = a_data.get("temperature", 0.7)
                    existing.max_tokens = a_data.get("max_tokens", 4096)
                    existing.strategy = Strategy(
                        a_data.get("strategy", "direct")
                    )
                    existing.tools = a_data.get("tools", []) or []
                    existing.system_prompt = a_data.get("system_prompt")

                    variant_val = a_data.get("variant")
                    existing.variant = (
                        AgentVariant(variant_val) if variant_val else None
                    )

                    if a_data.get("is_default", False):
                        await db.execute(
                            sa.update(AgentConfig)
                            .where(
                                AgentConfig.user_id == user_id,
                                AgentConfig.role
                                == AgentRole(a_data.get("role", "researcher")),
                                AgentConfig.is_default == True,
                                AgentConfig.id != existing.id,
                            )
                            .values(is_default=False)
                        )
                    existing.is_default = a_data.get("is_default", False)

                    agents_updated += 1
                else:
                    agents_skipped += 1
            else:
                if a_data.get("is_default", False):
                    await db.execute(
                        sa.update(AgentConfig)
                        .where(
                            AgentConfig.user_id == user_id,
                            AgentConfig.role
                            == AgentRole(a_data.get("role", "researcher")),
                            AgentConfig.is_default == True,
                        )
                        .values(is_default=False)
                    )

                variant_val = a_data.get("variant")
                agent = AgentConfig(
                    user_id=user_id,
                    name=name,
                    role=AgentRole(a_data.get("role", "researcher")),
                    provider=a_data.get("provider", "opencode"),
                    model=a_data.get("model", "gpt-4o"),
                    temperature=a_data.get("temperature", 0.7),
                    max_tokens=a_data.get("max_tokens", 4096),
                    strategy=Strategy(a_data.get("strategy", "direct")),
                    tools=a_data.get("tools", []) or [],
                    system_prompt=a_data.get("system_prompt"),
                    is_default=a_data.get("is_default", False),
                    variant=(
                        AgentVariant(variant_val) if variant_val else None
                    ),
                )
                db.add(agent)
                agents_created += 1

        # ----------------------------------------------------------------
        # Step 3 — Create M2M links (agent_skills)
        # ----------------------------------------------------------------
        for a_data in agents_data:
            skill_names: list[str] = a_data.get("skill_names", []) or []
            if not skill_names:
                continue

            a_result = await db.execute(
                select(AgentConfig).where(
                    AgentConfig.user_id == user_id,
                    AgentConfig.name == a_data["name"],
                )
            )
            agent = a_result.scalar_one_or_none()
            if agent is None:
                continue

            for s_name in skill_names:
                s_result = await db.execute(
                    select(Skill).where(
                        Skill.user_id == user_id, Skill.name == s_name
                    )
                )
                skill = s_result.scalar_one_or_none()
                if skill is None:
                    continue

                link_result = await db.execute(
                    sa.select(agent_skills_table).where(
                        agent_skills_table.c.agent_config_id == agent.id,
                        agent_skills_table.c.skill_id == skill.id,
                    )
                )
                if link_result.first() is None:
                    await db.execute(
                        agent_skills_table.insert().values(
                            agent_config_id=agent.id,
                            skill_id=skill.id,
                        )
                    )
                    links_created += 1

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    # --- mark staging consumed -----------------------------------------------
    staging.consumed = True

    return ImportResult(
        skills_created=skills_created,
        skills_updated=skills_updated,
        skills_skipped=skills_skipped,
        agent_configs_created=agents_created,
        agent_configs_updated=agents_updated,
        agent_configs_skipped=agents_skipped,
        agent_skills_links_created=links_created,
    )
