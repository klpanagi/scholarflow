"""Tests for research_dossier propagation across workflow stages (Task 13).

Verifies that when a stage (e.g. ScholarAgent) produces a research_dossier in
its result context, subsequent stages receive it in their agent_context.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.agents.dossier import (
    MethodologyEntry,
    PaperRecord,
    ResearchDossier,
    ResearchGap,
)
from app.models import AgentRole


def _make_dossier() -> ResearchDossier:
    return ResearchDossier(
        papers=[
            PaperRecord(
                paper_id="s2_001",
                title="Attention Is All You Need",
                authors=["Vaswani et al."],
                year=2017,
                citation_count=95000,
                abstract="The dominant sequence transduction models are based on "
                "complex recurrent or convolutional neural networks.",
            ),
            PaperRecord(
                paper_id="s2_002",
                title="BERT: Pre-training of Deep Bidirectional Transformers",
                authors=["Devlin et al."],
                year=2019,
                citation_count=70000,
            ),
        ],
        gaps=[
            ResearchGap(
                concept_a="transformers",
                concept_b="convolution",
                gap_score=0.85,
                supporting_papers=["s2_001"],
                confidence="high",
                description="Limited exploration of hybrid architectures",
            ),
        ],
        methodologies=[
            MethodologyEntry(
                paper_id="s2_001",
                method_name="Self-attention",
                dataset="WMT 2014",
                metrics=["BLEU"],
                baseline_methods=["RNN"],
                result="28.4 BLEU",
                confidence="high",
            ),
        ],
        generated_at=datetime(2025, 1, 1),
    )


def _make_config(role: AgentRole | None = None) -> MagicMock:
    config = MagicMock()
    config.name = "test-agent"
    config.role = role or AgentRole.RESEARCHER
    config.model = "test-model"
    config.provider = "test-provider"
    config.strategy = MagicMock(value="direct")
    config.skills = []
    config.system_prompt = "Test system prompt"
    config.temperature = 0.7
    config.max_tokens = 4096
    return config


class TestRunStageReturnsDossier:

    @pytest.mark.asyncio
    async def test_run_stage_returns_dossier_when_agent_produces_one(self):
        """When agent.run() returns context with research_dossier, _run_stage includes it."""
        dossier = _make_dossier()
        config = _make_config()

        agent_result = {
            "output": "Search results with papers found.",
            "context": {"research_dossier": dossier, "rating": 8.5},
            "metadata": {"usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}},
        }

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=agent_result)
        mock_db = AsyncMock()

        with (
            patch("app.api.routes.workflows._get_user_config_by_id", new_callable=AsyncMock, return_value=config),
            patch("app.api.routes.workflows.create_agent", return_value=mock_agent),
            patch("app.api.routes.workflows.fetch_model_pricing", new_callable=AsyncMock, return_value={}),
            patch("app.api.routes.workflows.calculate_cost", return_value=0.0),
            patch("app.api.routes.workflows.model_supports_pdf", return_value=False),
            patch("app.api.routes.workflows.evaluate_rubric", new_callable=AsyncMock, return_value=None),
        ):
            from app.api.routes.workflows import _run_stage

            stage_def = {
                "id": "search-related-work",
                "role": AgentRole.RESEARCHER.value,
                "task_template": "Search: {input}",
            }

            result = await _run_stage(
                db=mock_db,
                user_id="user1",
                stage_def=stage_def,
                context="test paper content",
                config_id=uuid4(),
            )

        assert "research_dossier" in result
        assert result["research_dossier"] is not None
        assert result["research_dossier"] is dossier

    @pytest.mark.asyncio
    async def test_run_stage_returns_none_dossier_when_agent_has_no_dossier(self):
        """When agent.run() returns no dossier, _run_stage returns dossier=None."""
        config = _make_config()

        agent_result = {
            "output": "No dossier produced.",
            "context": {"rating": 5.0},
            "metadata": {"usage": {"input_tokens": 50, "output_tokens": 30, "total_tokens": 80}},
        }

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=agent_result)
        mock_db = AsyncMock()

        with (
            patch("app.api.routes.workflows._get_user_config_by_id", new_callable=AsyncMock, return_value=config),
            patch("app.api.routes.workflows.create_agent", return_value=mock_agent),
            patch("app.api.routes.workflows.fetch_model_pricing", new_callable=AsyncMock, return_value={}),
            patch("app.api.routes.workflows.calculate_cost", return_value=0.0),
            patch("app.api.routes.workflows.model_supports_pdf", return_value=False),
            patch("app.api.routes.workflows.evaluate_rubric", new_callable=AsyncMock, return_value=None),
        ):
            from app.api.routes.workflows import _run_stage

            stage_def = {
                "id": "review-paper",
                "role": AgentRole.REVIEWER.value,
                "task_template": "Review: {input}",
            }

            result = await _run_stage(
                db=mock_db,
                user_id="user1",
                stage_def=stage_def,
                context="test paper content",
                config_id=uuid4(),
            )

        assert "research_dossier" in result
        assert result["research_dossier"] is None


class TestDossierPropagatesToNextStage:

    @pytest.mark.asyncio
    async def test_dossier_injected_into_next_stage_agent_context(self):
        """Stage 2 receives dossier in its agent_context when provided."""
        dossier = _make_dossier()
        config = _make_config()

        captured_contexts = []

        async def mock_run(messages, context=None, thread_id=None):
            captured_contexts.append(dict(context) if context else {})
            return {
                "output": "Review completed.",
                "context": {"analysis": "Good paper"},
                "metadata": {"usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}},
            }

        mock_agent = MagicMock()
        mock_agent.run = mock_run
        mock_db = AsyncMock()

        with (
            patch("app.api.routes.workflows._get_user_config_by_id", new_callable=AsyncMock, return_value=config),
            patch("app.api.routes.workflows.create_agent", return_value=mock_agent),
            patch("app.api.routes.workflows.fetch_model_pricing", new_callable=AsyncMock, return_value={}),
            patch("app.api.routes.workflows.calculate_cost", return_value=0.0),
            patch("app.api.routes.workflows.model_supports_pdf", return_value=False),
            patch("app.api.routes.workflows.evaluate_rubric", new_callable=AsyncMock, return_value=None),
        ):
            from app.api.routes.workflows import _run_stage

            stage_def = {
                "id": "review-paper",
                "role": AgentRole.REVIEWER.value,
                "task_template": "Review: {input}",
            }

            result = await _run_stage(
                db=mock_db,
                user_id="user1",
                stage_def=stage_def,
                context="review this paper",
                config_id=uuid4(),
                research_dossier=dossier,
            )

        assert len(captured_contexts) == 1
        assert "research_dossier" in captured_contexts[0]
        assert captured_contexts[0]["research_dossier"] is dossier


class TestEndToEndDossierPropagation:

    @pytest.mark.asyncio
    async def test_two_stage_workflow_dossier_flows_to_reviewer(self):
        """Simulate Scholar → Reviewer workflow; reviewer receives dossier."""
        dossier = _make_dossier()
        scholar_config = _make_config(AgentRole.RESEARCHER)
        reviewer_config = _make_config(AgentRole.REVIEWER)

        scholar_result = {
            "output": "Found relevant papers...",
            "context": {"research_dossier": dossier, "rating": 8.0},
            "metadata": {"usage": {"input_tokens": 200, "output_tokens": 100, "total_tokens": 300}},
        }

        reviewer_contexts = []

        async def mock_run_scholar(messages, context=None, thread_id=None):
            return scholar_result

        async def mock_run_reviewer(messages, context=None, thread_id=None):
            reviewer_contexts.append(dict(context) if context else {})
            return {
                "output": "The paper is strong.",
                "context": {"analysis": "Analyzed with dossier"},
                "metadata": {"usage": {"input_tokens": 150, "output_tokens": 80, "total_tokens": 230}},
            }

        mock_db = AsyncMock()

        scholar_agent = MagicMock()
        scholar_agent.run = mock_run_scholar

        with (
            patch("app.api.routes.workflows._get_user_config_by_id", new_callable=AsyncMock, return_value=scholar_config),
            patch("app.api.routes.workflows.create_agent", return_value=scholar_agent),
            patch("app.api.routes.workflows.fetch_model_pricing", new_callable=AsyncMock, return_value={}),
            patch("app.api.routes.workflows.calculate_cost", return_value=0.0),
            patch("app.api.routes.workflows.model_supports_pdf", return_value=False),
            patch("app.api.routes.workflows.evaluate_rubric", new_callable=AsyncMock, return_value=None),
        ):
            from app.api.routes.workflows import _run_stage

            result1 = await _run_stage(
                db=mock_db,
                user_id="user1",
                stage_def={"id": "search", "role": AgentRole.RESEARCHER.value, "task_template": "Search: {input}"},
                context="original paper",
                config_id=uuid4(),
            )

        assert result1["research_dossier"] is not None

        current_dossier = result1.get("research_dossier")

        reviewer_agent = MagicMock()
        reviewer_agent.run = mock_run_reviewer

        with (
            patch("app.api.routes.workflows._get_user_config_by_id", new_callable=AsyncMock, return_value=reviewer_config),
            patch("app.api.routes.workflows.create_agent", return_value=reviewer_agent),
            patch("app.api.routes.workflows.fetch_model_pricing", new_callable=AsyncMock, return_value={}),
            patch("app.api.routes.workflows.calculate_cost", return_value=0.0),
            patch("app.api.routes.workflows.model_supports_pdf", return_value=False),
            patch("app.api.routes.workflows.evaluate_rubric", new_callable=AsyncMock, return_value=None),
        ):
            result2 = await _run_stage(
                db=mock_db,
                user_id="user1",
                stage_def={"id": "review", "role": AgentRole.REVIEWER.value, "task_template": "Review: {input}"},
                context="review this paper",
                config_id=uuid4(),
                research_dossier=current_dossier,
            )

        assert len(reviewer_contexts) == 1
        assert "research_dossier" in reviewer_contexts[0]
        assert reviewer_contexts[0]["research_dossier"] is dossier

        injected_dossier = reviewer_contexts[0]["research_dossier"]
        assert len(injected_dossier.papers) == 2
        assert injected_dossier.papers[0].title == "Attention Is All You Need"
        assert len(injected_dossier.gaps) == 1
        assert injected_dossier.gaps[0].concept_a == "transformers"
