from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_user
from app.core.security import get_current_user
from app.models import AgentConfig, AgentRole, Strategy
from app.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    AgentConfigCreate,
    AgentConfigUpdate,
    AgentConfigResponse,
    AgentListResponse,
)
from app.agents.factory import create_agent, enum_value, list_agents
from app.tools import get_tools_by_names
from app.seeds.scholarflow_skills import seed_scholarflow

router = APIRouter(prefix="/agents", tags=["agents"])


def _get_existing_roles(configs: list[AgentConfig]) -> set[AgentRole]:
    return {c.role for c in configs}


@router.get("/types", response_model=AgentListResponse)
async def get_available_agents():
    agents = list_agents()
    return {"agents": agents}


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    request: AgentRunRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_user(user_id, db)

    system_prompt = None
    model = request.model
    provider = "opencode"
    strategy = request.strategy or "direct"
    temperature = 0.7
    max_tokens = 4096

    if request.agent_config_id:
        result = await db.execute(
            select(AgentConfig)
            .options(selectinload(AgentConfig.skills))
            .where(
                AgentConfig.id == request.agent_config_id,
                (AgentConfig.user_id.is_(None)) | (AgentConfig.user_id == current_user.id),
            )
        )
        config = result.scalar_one_or_none()
        if config:
            model = model or config.model
            provider = config.provider
            strategy = strategy if request.strategy else enum_value(config.strategy)
            system_prompt = config.system_prompt
            temperature = config.temperature
            max_tokens = config.max_tokens
            skill_prompts = [s.prompt_template for s in config.skills if s.prompt_template]
            skill_tools = config.get_tool_names()
        else:
            skill_prompts = []
            skill_tools = []
    else:
        skill_prompts = []
        skill_tools = []

    if skill_prompts:
        system_prompt = "\n\n".join(filter(None, [system_prompt] + skill_prompts))

    resolved_tools = get_tools_by_names(skill_tools) if skill_tools else []

    try:
        agent = create_agent(
            agent_type=request.agent_type,
            model=model,
            provider=provider,
            strategy=strategy,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=resolved_tools,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    from langchain_core.messages import HumanMessage

    messages = [HumanMessage(content=request.message)]
    result = await agent.run(
        messages=messages,
        context=request.context or {},
        thread_id=request.thread_id,
    )

    return {
        "output": result.get("output", ""),
        "metadata": {**result.get("metadata", {}), "skills_used": skill_tools},
    }


@router.post("/configs", response_model=AgentConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_config(
    config_data: AgentConfigCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_user(user_id, db)

    try:
        role = AgentRole(config_data.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in AgentRole]}",
        )

    try:
        strategy = Strategy(config_data.strategy)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid strategy. Must be one of: {[s.value for s in Strategy]}",
        )

    config = AgentConfig(
        user_id=current_user.id,
        name=config_data.name,
        role=role,
        provider=config_data.provider,
        model=config_data.model,
        temperature=config_data.temperature,
        max_tokens=config_data.max_tokens,
        strategy=strategy,
        tools=config_data.tools,
        system_prompt=config_data.system_prompt,
        is_default=config_data.is_default,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/configs", response_model=list[AgentConfigResponse])
async def list_agent_configs(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_user(user_id, db)

    # Ensure global defaults exist (idempotent) — runs once on first call ever
    global_configs_result = await db.execute(
        select(AgentConfig)
        .options(selectinload(AgentConfig.skills))
        .where(AgentConfig.user_id.is_(None))
    )
    global_configs = list(global_configs_result.scalars().all())
    if not global_configs:
        await seed_scholarflow(db)

    # Query global + user configs, merge by name (user override wins)
    result = await db.execute(
        select(AgentConfig)
        .options(selectinload(AgentConfig.skills))
        .where(
            (AgentConfig.user_id.is_(None)) | (AgentConfig.user_id == current_user.id)
        )
    )
    all_configs = result.scalars().all()

    by_name: dict[str, AgentConfig] = {}
    user_id_str = str(current_user.id)
    for c in all_configs:
        name = str(c.name)
        existing = by_name.get(name)
        c_user_id = str(c.user_id) if c.user_id else None
        if existing is None or (c_user_id == user_id_str and str(existing.user_id) != user_id_str):
            by_name[name] = c

    return list(by_name.values())


@router.get("/configs/{config_id}", response_model=AgentConfigResponse)
async def get_agent_config(
    config_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_user(user_id, db)
    result = await db.execute(
        select(AgentConfig)
        .options(selectinload(AgentConfig.skills))
        .where(
            AgentConfig.id == config_id,
            (AgentConfig.user_id.is_(None)) | (AgentConfig.user_id == current_user.id),
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
    return config


@router.patch("/configs/{config_id}", response_model=AgentConfigResponse)
async def update_agent_config(
    config_id: str,
    config_data: AgentConfigUpdate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_user(user_id, db)
    result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.id == config_id,
            AgentConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    update_data = config_data.model_dump(exclude_unset=True)

    if "role" in update_data:
        try:
            update_data["role"] = AgentRole(update_data["role"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {[r.value for r in AgentRole]}",
            )

    if "strategy" in update_data:
        try:
            update_data["strategy"] = Strategy(update_data["strategy"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy. Must be one of: {[s.value for s in Strategy]}",
            )

    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_config(
    config_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_user(user_id, db)
    result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.id == config_id,
            AgentConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    await db.delete(config)
    await db.commit()
