from typing import Any, Optional, Union

from langchain_core.language_models import BaseChatModel  # noqa: F401  (kept for type-hint parity)

from app.agents.base import BaseAgent
from app.agents.debate_agent import DebateAgent
from app.agents.deep_debate_agent import DeepDebateAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.review_agent import ReviewAgent
from app.agents.review_pipeline import DeepReviewAgent
from app.agents.review_writer_agent import ReviewWriterAgent
from app.agents.revision_agent import RevisionAgent
from app.agents.search_agent import SearchAgent
from app.agents.simple_debate_agent import SimpleDebateAgent
from app.agents.writing_agent import WritingAgent
from app.services.llm_service import llm_service


from app.models import AgentRole

# Two-level registry: role → variant (optional) → class. For most roles the
# value is a class directly. For DEBATER the value is a dict mapping variant
# name → class, allowing the factory to dispatch to SimpleDebateAgent,
# DebateAgent, or DeepDebateAgent based on a runtime ``variant`` argument.
AGENT_REGISTRY: dict[str, Union[type[BaseAgent], dict[str, type[BaseAgent]]]] = {
    AgentRole.RESEARCHER.value: SearchAgent,
    AgentRole.WRITER.value: WritingAgent,
    AgentRole.REVIEWER.value: ReviewAgent,
    AgentRole.REVIEW_WRITER.value: ReviewWriterAgent,
    AgentRole.RECOMMENDER.value: RecommendationAgent,
    AgentRole.REVISION.value: RevisionAgent,
    AgentRole.MANAGER.value: WritingAgent,
    AgentRole.DEBATER.value: {
        "simple": SimpleDebateAgent,
        "standard": DebateAgent,
        "deep": DeepDebateAgent,
    },
    AgentRole.DEEP_REVIEWER.value: DeepReviewAgent,
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
