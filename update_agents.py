import sys
content = open("backend/app/api/routes/agents.py").read()

new_logic = """
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
                provider="opencode",
                model="gpt-4o",
                strategy=Strategy.DIRECT,
                system_prompt="You are an expert academic researcher. You find literature, verify novelty, and extract insights.",
                is_default=True
            ),
            AgentConfig(
                user_id=current_user.id,
                name="Default Writer",
                role=AgentRole.WRITER,
                provider="opencode",
                model="gpt-4o",
                strategy=Strategy.DIRECT,
                system_prompt="You are an expert academic writer. You write clear, well-structured scientific prose following IMRaD and grant proposal standards.",
                is_default=True
            ),
            AgentConfig(
                user_id=current_user.id,
                name="Default Reviewer",
                role=AgentRole.REVIEWER,
                provider="opencode",
                model="gpt-4o",
                strategy=Strategy.CRITIQUE,
                system_prompt="You are a rigorous peer reviewer. You critique papers for novelty, soundness, and presentation.",
                is_default=True
            ),
            AgentConfig(
                user_id=current_user.id,
                name="Default Recommender",
                role=AgentRole.RECOMMENDER,
                provider="opencode",
                model="gpt-4o",
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
"""

import re
content = re.sub(r'@router.get\("/configs", response_model=list\[AgentConfigResponse\]\)\nasync def list_agent_configs\([\s\S]*?return result\.scalars\(\)\.all\(\)', new_logic.strip(), content)

open("backend/app/api/routes/agents.py", "w").write(content)
