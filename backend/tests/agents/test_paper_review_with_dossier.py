"""Tests for ReviewAgent dossier augmentation (Task 11).

Verifies that the analyze node prepends a ResearchDossier context section
to the analysis prompt when a dossier is present in state["context"].
"""

from datetime import datetime

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.base import AgentState
from app.agents.dossier import (
    MethodologyEntry,
    PaperRecord,
    ResearchDossier,
    ResearchGap,
)
from app.agents.review_agent import ReviewAgent
from app.agents.strategies import EventType, StrategyEvent


def _make_dossier(
    n_papers: int = 3,
    n_gaps: int = 2,
    n_methods: int = 2,
) -> ResearchDossier:
    papers = []
    for i in range(n_papers):
        papers.append(
            PaperRecord(
                paper_id=f"paper_{i}",
                title=f"Paper Title {i}",
                authors=[f"Author {i}"],
                year=2020 + i,
                citation_count=100 * (i + 1),
                abstract=f"Abstract for paper {i}",
            )
        )

    gaps = []
    for i in range(n_gaps):
        gaps.append(
            ResearchGap(
                concept_a=f"Concept A{i}",
                concept_b=f"Concept B{i}",
                gap_score=0.8 - i * 0.1,
                supporting_papers=[f"paper_{i}"],
                confidence="high" if i == 0 else "medium",
                description=f"Gap description {i}",
            )
        )

    methods = []
    for i in range(n_methods):
        methods.append(
            MethodologyEntry(
                paper_id=f"paper_{i}",
                method_name=f"Method {i}",
                dataset=f"Dataset {i}",
                metrics=["BLEU", "ROUGE"],
                baseline_methods=["Baseline"],
                result=f"{90 + i:.1f}% accuracy",
                confidence="high",
            )
        )

    return ResearchDossier(
        papers=papers,
        gaps=gaps,
        methodologies=methods,
        generated_at=datetime(2025, 1, 1),
    )


def _make_state(
    user_msg: str = "Please review this paper on transformers.",
    context: dict | None = None,
) -> AgentState:
    return AgentState(
        messages=[HumanMessage(content=user_msg)],
        context=context or {},
        output=None,
        metadata={},
    )


class TestReviewerUsesDossierWhenPresent:
    @pytest.mark.asyncio
    async def test_reviewer_uses_dossier_when_present(self, mock_llm):
        agent = ReviewAgent(llm=mock_llm)
        dossier = _make_dossier(n_papers=3, n_gaps=2, n_methods=2)
        state = _make_state(context={"research_dossier": dossier})

        captured_content = []

        async def capturing_execute(llm, messages, system_prompt, tools=None):
            captured_content.extend([m.content for m in messages])
            yield StrategyEvent(
                type=EventType.STRATEGY_COMPLETE,
                phase="complete",
                iteration=1,
                max_iterations=1,
                result=AIMessage(content="Analyzed"),
            )

        agent.strategy.execute = capturing_execute

        graph = agent.build_graph()
        compiled = graph.compile()
        await compiled.ainvoke(
            state, config={"configurable": {"thread_id": "test"}}
        )

        analysis_prompt = " ".join(captured_content)
        assert "Top related papers" in analysis_prompt
        assert "Paper Title 0" in analysis_prompt
        assert "Identified research gaps" in analysis_prompt
        assert "Concept A0" in analysis_prompt
        assert "Methodology landscape" in analysis_prompt
        assert "Method 0" in analysis_prompt


class TestReviewerUnchangedWithoutDossier:
    @pytest.mark.asyncio
    async def test_reviewer_unchanged_without_dossier(self, mock_llm):
        agent = ReviewAgent(llm=mock_llm)
        state = _make_state(context={})

        captured_content = []

        async def capturing_execute(llm, messages, system_prompt, tools=None):
            captured_content.extend([m.content for m in messages])
            yield StrategyEvent(
                type=EventType.STRATEGY_COMPLETE,
                phase="complete",
                iteration=1,
                max_iterations=1,
                result=AIMessage(content="Analyzed"),
            )

        agent.strategy.execute = capturing_execute

        graph = agent.build_graph()
        compiled = graph.compile()
        await compiled.ainvoke(
            state, config={"configurable": {"thread_id": "test"}}
        )

        analysis_prompt = " ".join(captured_content)
        assert "Available Evidence Corpus" not in analysis_prompt
        assert "Top related papers" not in analysis_prompt
        assert "Analyze this document" in analysis_prompt
        assert "Core contribution and significance" in analysis_prompt


class TestReviewerHandlesEmptyDossier:
    @pytest.mark.asyncio
    async def test_reviewer_handles_empty_dossier(self, mock_llm):
        agent = ReviewAgent(llm=mock_llm)
        dossier = _make_dossier(n_papers=0, n_gaps=0, n_methods=0)
        state = _make_state(context={"research_dossier": dossier})

        captured_content = []

        async def capturing_execute(llm, messages, system_prompt, tools=None):
            captured_content.extend([m.content for m in messages])
            yield StrategyEvent(
                type=EventType.STRATEGY_COMPLETE,
                phase="complete",
                iteration=1,
                max_iterations=1,
                result=AIMessage(content="Analyzed"),
            )

        agent.strategy.execute = capturing_execute

        graph = agent.build_graph()
        compiled = graph.compile()
        await compiled.ainvoke(
            state, config={"configurable": {"thread_id": "test"}}
        )

        analysis_prompt = " ".join(captured_content)
        assert "Top related papers" in analysis_prompt
        assert "Available Evidence Corpus" in analysis_prompt
