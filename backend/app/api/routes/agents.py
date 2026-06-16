from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, AgentConfig, AgentRole, Strategy, Skill
from app.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    AgentConfigCreate,
    AgentConfigUpdate,
    AgentConfigResponse,
    AgentListResponse,
)
from app.agents.factory import create_agent, list_agents
from app.tools import get_tools_by_names

router = APIRouter(prefix="/agents", tags=["agents"])


async def _get_user(user_id: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


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
    current_user = await _get_user(user_id, db)

    system_prompt = None
    model = request.model
    provider = "opencode"
    strategy = request.strategy or "direct"
    temperature = 0.7
    max_tokens = 4096
    skill_prompts = []
    skill_tools = []

    if request.agent_config_id:
        result = await db.execute(
            select(AgentConfig)
            .options(selectinload(AgentConfig.skills))
            .where(
                AgentConfig.id == request.agent_config_id,
                AgentConfig.user_id == current_user.id,
            )
        )
        config = result.scalar_one_or_none()
        if config:
            model = model or config.model
            provider = config.provider
            strategy = strategy if request.strategy else (config.strategy.value if hasattr(config.strategy, 'value') else config.strategy)
            system_prompt = config.system_prompt
            temperature = config.temperature
            max_tokens = config.max_tokens
            for skill in config.skills:
                if skill.prompt_template:
                    skill_prompts.append(skill.prompt_template)
                if skill.builtin_tools:
                    skill_tools.extend(skill.builtin_tools)

    if skill_prompts:
        combined_prompt = "\n\n".join(filter(None, [system_prompt] + skill_prompts))
        system_prompt = combined_prompt

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
    current_user = await _get_user(user_id, db)

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
    current_user = await _get_user(user_id, db)
    result = await db.execute(
        select(AgentConfig)
        .options(selectinload(AgentConfig.skills))
        .where(AgentConfig.user_id == current_user.id)
    )
    configs = result.scalars().all()
    
    if not configs:
        # Create default configs
        defaults = [
            AgentConfig(
                user_id=current_user.id,
                name="Default Researcher",
                role=AgentRole.RESEARCHER,
                provider="openrouter",
                model="google/gemma-4-31b-it:free",
                strategy=Strategy.DIRECT,
                system_prompt="You are an expert academic researcher. You find literature, verify novelty, and extract insights.",
                is_default=True
            ),
            AgentConfig(
                user_id=current_user.id,
                name="Default Writer",
                role=AgentRole.WRITER,
                provider="openrouter",
                model="google/gemma-4-31b-it:free",
                strategy=Strategy.DIRECT,
                system_prompt="You are an expert academic writer. You write clear, well-structured scientific prose following IMRaD and grant proposal standards.",
                is_default=True
            ),
            AgentConfig(
                user_id=current_user.id,
                name="Default Reviewer",
                role=AgentRole.REVIEWER,
                provider="openrouter",
                model="google/gemma-4-31b-it:free",
                strategy=Strategy.CRITIQUE,
                system_prompt="You are a rigorous peer reviewer. You critique papers for novelty, soundness, and presentation.",
                is_default=True
            ),
            AgentConfig(
                user_id=current_user.id,
                name="Default Recommender",
                role=AgentRole.RECOMMENDER,
                provider="openrouter",
                model="google/gemma-4-31b-it:free",
                strategy=Strategy.DIRECT,
                system_prompt="You are a personalized academic recommendation engine. You suggest relevant papers and venues.",
                is_default=True
            )
        ]
        db.add_all(defaults)
        await db.commit()
        for d in defaults:
            await db.refresh(d)
        configs = defaults

    return configs


@router.get("/configs/{config_id}", response_model=AgentConfigResponse)
async def get_agent_config(
    config_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    result = await db.execute(
        select(AgentConfig)
        .options(selectinload(AgentConfig.skills))
        .where(
            AgentConfig.id == config_id,
            AgentConfig.user_id == current_user.id,
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
    current_user = await _get_user(user_id, db)
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
    current_user = await _get_user(user_id, db)
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
