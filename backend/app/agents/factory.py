from typing import Any

from langchain_core.language_models import BaseChatModel

from app.agents.base import BaseAgent
from app.agents.scholar_agent import ScholarAgent
from app.agents.writing_agent import WritingAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.review_pipeline import PaperReviewAgent
from app.services.llm_service import llm_service


from app.models import AgentRole

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    AgentRole.RESEARCHER.value: ScholarAgent,
    AgentRole.WRITER.value: WritingAgent,
    AgentRole.REVIEWER.value: PaperReviewAgent,
    AgentRole.RECOMMENDER.value: RecommendationAgent,
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
    **kwargs,
) -> BaseAgent:
    agent_cls = AGENT_REGISTRY.get(agent_type)
    if not agent_cls:
        raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(AGENT_REGISTRY.keys())}")

    llm = llm_service.get_llm(
        model=model,
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return agent_cls(llm=llm, strategy_name=strategy, system_prompt=system_prompt, tools=tools, **kwargs)


def list_agents() -> list[dict[str, str]]:
    return [
        {"name": name, "description": cls.description}
        for name, cls in AGENT_REGISTRY.items()
    ]
