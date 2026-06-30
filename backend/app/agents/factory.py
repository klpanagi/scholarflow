from typing import Any, Optional, Union

from langchain_core.language_models import BaseChatModel  # noqa: F401  (kept for type-hint parity)

from app.agents.base import BaseAgent
from app.agents.chat_agent import ChatAgent
from app.agents.debate_agent import DebateAgent
from app.agents.deep_debate_agent import DeepDebateAgent
from app.agents.manager_agent import ManagerAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.review_agent import ReviewAgent
from app.agents.review_pipeline import DeepReviewAgent
from app.agents.revision_agent import RevisionAgent
from app.agents.search_agent import SearchAgent
from app.agents.simple_debate_agent import SimpleDebateAgent
from app.agents.writing_agent import WritingAgent
from app.services.llm_service import llm_service


from app.models import AgentConfig, AgentRole

# Two-level registry: role → variant (optional) → class. For most roles the
# value is a class directly. For DEBATER the value is a dict mapping variant
# name → class, allowing the factory to dispatch to SimpleDebateAgent,
# DebateAgent, or DeepDebateAgent based on a runtime ``variant`` argument.
AGENT_REGISTRY: dict[str, Union[type[BaseAgent], dict[str, type[BaseAgent]]]] = {
    AgentRole.RESEARCHER.value: SearchAgent,
    AgentRole.WRITER.value: WritingAgent,
    AgentRole.REVIEWER.value: ReviewAgent,
    AgentRole.RECOMMENDER.value: RecommendationAgent,
    AgentRole.REVISION.value: RevisionAgent,
    AgentRole.MANAGER.value: ManagerAgent,
    AgentRole.DEBATER.value: {
        "simple": SimpleDebateAgent,
        "standard": DebateAgent,
        "deep": DeepDebateAgent,
    },
    AgentRole.DEEP_REVIEWER.value: DeepReviewAgent,
    AgentRole.CHAT.value: ChatAgent,
}


def create_agent(
    agent_type: str,
    model: str | None = None,
    provider: str = "opencode",
    strategy: str = "direct",
    system_prompt: str | None = None,
    tools: list[Any] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    variant: Optional[str] = None,
    **kwargs,
) -> BaseAgent:
    agent_cls = AGENT_REGISTRY.get(agent_type)
    if not agent_cls:
        raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(AGENT_REGISTRY.keys())}")

    # Variant dispatch: when the registered value is a dict, look up the
    # variant. Unknown variant names raise ValueError so callers see the
    # full list of supported variants rather than a generic KeyError.
    if isinstance(agent_cls, dict):
        if variant is None:
            variant = "simple"  # default for backward compat
        if variant not in agent_cls:
            raise ValueError(
                f"Unknown variant '{variant}' for agent type '{agent_type}'. "
                f"Available variants: {list(agent_cls.keys())}"
            )
        agent_cls = agent_cls[variant]

    llm = llm_service.get_llm(
        model=model,
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return agent_cls(llm=llm, strategy_name=strategy, system_prompt=system_prompt, tools=tools, **kwargs)


def enum_value(val: Any):
    """Extract value from an enum member or return the value as-is.

    Avoids the ``hasattr(x, 'value')`` pattern that was repeated
    across multiple call sites.
    """
    return val.value if hasattr(val, "value") else val


def build_agent_from_config(
    config: AgentConfig,
    *,
    prompt_join_style: str = "default",
    strategy_override: str | None = None,
) -> tuple[BaseAgent, list[str]]:
    """Create a LangGraph agent from a persisted ``AgentConfig`` row.

    Handles the common boilerplate:
    * Extracting skill prompts and tool names
    * Resolving tool references
    * Building a combined system prompt
    * Extracting enum values for ``role``, ``strategy``, and ``variant``

    Parameters
    ----------
    config:
        ``AgentConfig`` instance with its ``skills`` relationship eagerly
        loaded (e.g. via ``selectinload(AgentConfig.skills)``).
    prompt_join_style:
        How to combine the config's ``system_prompt`` with its skill prompts.

        * ``"default"`` — ``"\\n\\n".join(filter(None, ...))``
        * ``"workflows"`` — appends with ``"Additional knowledge:\\n---"``
    strategy_override:
        When provided, overrides the strategy from the config.  Used by
        endpoints that accept a runtime strategy from the client.

    Returns
    -------
    ``(agent, tool_names)`` where ``tool_names`` are the names of the
    tools associated with the config (needed for response metadata).
    """
    from app.tools import get_tools_by_names

    skill_prompts = [s.prompt_template for s in config.skills if s.prompt_template]
    tool_names = config.get_tool_names()
    resolved_tools = get_tools_by_names(tool_names) if tool_names else []

    system_prompt = config.system_prompt or ""
    if skill_prompts:
        if prompt_join_style == "workflows":
            system_prompt += (
                "\n\nAdditional knowledge:\n" + "\n---\n".join(skill_prompts)
            )
        else:
            system_prompt = "\n\n".join(filter(None, [system_prompt] + skill_prompts))

    agent_type = enum_value(config.role)
    strategy = strategy_override or enum_value(config.strategy)
    variant = enum_value(getattr(config, "variant", None))

    agent = create_agent(
        agent_type=agent_type,
        model=config.model,
        provider=config.provider,
        strategy=strategy,
        system_prompt=system_prompt,
        tools=resolved_tools,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        variant=variant,
    )
    return agent, tool_names


def list_agents() -> list[dict[str, str]]:
    """List all available agent types and their variants.

    For most roles, returns a single entry. For DEBATER, returns one entry
    per variant so that clients can discover all available configurations.
    """
    result: list[dict[str, str]] = []
    for name, value in AGENT_REGISTRY.items():
        if isinstance(value, dict):
            for variant_name, variant_cls in value.items():
                result.append(
                    {
                        "name": f"{name}:{variant_name}",
                        "description": variant_cls.description,
                        "role": name,
                        "variant": variant_name,
                    }
                )
        else:
            result.append(
                {
                    "name": name,
                    "description": value.description,
                    "role": name,
                    "variant": "",
                }
            )
    return result
