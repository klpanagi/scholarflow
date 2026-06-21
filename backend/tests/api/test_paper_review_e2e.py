"""End-to-end tests for paper-review workflow dossier propagation through all 5 stages.

Tests the full 5-stage ``_run_workflow_background()`` orchestrator loop, verifying that
the ``research_dossier`` produced by one stage propagates through subsequent stages via
the ``current_dossier`` mechanism (line 1104 in workflows.py).

Contrasts with test_workflow_dossier_propagation.py which only tests ``_run_stage``
directly with 1-2 stages in isolation.
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


# ---------------------------------------------------------------------------
# Helpers (duplicated from test_workflow_dossier_propagation for clarity)
# ---------------------------------------------------------------------------

def _make_dossier() -> ResearchDossier:
    """Create a test ResearchDossier instance."""
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
    """Create a mock agent config with the given role."""
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


def _make_agent_result(output: str, context: dict | None = None) -> dict:
    """Create a standard agent run result dict matching the shape _run_stage expects."""
    return {
        "output": output,
        "context": context or {},
        "metadata": {"usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}},
    }


# Paper-review workflow stage IDs (from WORKFLOW_DEFINITIONS)
STAGE_IDS = [
    "search-related-work",
    "review-paper",
    "debate-review",
    "refine-review",
    "response-to-editor",
]


# ---------------------------------------------------------------------------
# E2E tests
# ---------------------------------------------------------------------------

class TestPaperReviewWorkflowE2E:
    """End-to-end tests for the 5-stage paper-review workflow dossier propagation."""

    @pytest.mark.asyncio
    async def test_paper_review_workflow_propagates_dossier_through_all_5_stages(self):
        """Dossier from stage 1 (Scholar) reaches stages 2-5 via current_dossier fallback.

        Scenario:
          - Stage 1 (search-related-work): produces a ResearchDossier
          - Stages 2-5: produce NO dossier (only output text)

        Assert:
          - Stages 2, 3, 4, 5 each receive the *same* dossier instance in agent_context
          - Workflow completes successfully with all 5 stages
        """
        dossier = _make_dossier()

        # --- mock agents (returned in order by create_agent) ---
        mock_scholar = MagicMock()
        mock_scholar.run = AsyncMock(return_value=_make_agent_result(
            "Search results found.",
            context={"research_dossier": dossier, "rating": 8.5},
        ))

        mock_reviewer = MagicMock()
        mock_reviewer.run = AsyncMock(return_value=_make_agent_result("Review done."))

        mock_debater = MagicMock()
        mock_debater.run = AsyncMock(return_value=_make_agent_result("Debate done."))

        mock_writer1 = MagicMock()
        mock_writer1.run = AsyncMock(return_value=_make_agent_result("Refine done."))

        mock_writer2 = MagicMock()
        mock_writer2.run = AsyncMock(return_value=_make_agent_result("Editor done."))

        agents = [mock_scholar, mock_reviewer, mock_debater, mock_writer1, mock_writer2]

        # --- agent assignments: stage_id -> config_id_str ---
        assignments = {sid: str(uuid4()) for sid in STAGE_IDS}
        config = _make_config()
        config_map = {cid: config for cid in assignments.values()}

        async def mock_get_config(_db, _user_id, config_id):
            return config_map.get(str(config_id))

        agent_iter = iter(agents)

        def create_agent_side_effect(*_args, **_kwargs):
            return next(agent_iter)

        # --- mock DB session ---
        mock_execution = MagicMock()
        mock_execution.id = uuid4()
        mock_execution.stages = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = False

        # --- patch and run ---
        with (
            patch("app.api.routes.workflows.AsyncSessionLocal", return_value=mock_session_cm),
            patch("app.api.routes.workflows._get_user_config_by_id", side_effect=mock_get_config),
            patch("app.api.routes.workflows.create_agent", side_effect=create_agent_side_effect),
            patch("app.api.routes.workflows.fetch_model_pricing", new_callable=AsyncMock, return_value={}),
            patch("app.api.routes.workflows.calculate_cost", return_value=0.0),
            patch("app.api.routes.workflows.model_supports_pdf", return_value=False),
            patch("app.api.routes.workflows.evaluate_rubric", new_callable=AsyncMock, return_value=None),
            patch("app.api.routes.workflows._build_stage_context", side_effect=lambda orig, _find: orig),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            from app.api.routes.workflows import _run_workflow_background

            await _run_workflow_background(
                execution_id=str(uuid4()),
                user_id="test-user",
                workflow_id="paper-review",
                original_context="Test paper content",
                pdf_bytes=None,
                paper_s2_id=None,
                topic_query="test query",
                agent_assignments=assignments,
                paper_content=None,
                rubric_standard="general",
            )

        # --- assertions: stages 2-5 received the SAME dossier instance (identity) ---
        for agent in [mock_reviewer, mock_debater, mock_writer1, mock_writer2]:
            agent.run.assert_called_once()
            ctx = agent.run.call_args.kwargs["context"]
            assert "research_dossier" in ctx, (
                f"Agent {agent} did not receive research_dossier in context"
            )
            assert ctx["research_dossier"] is dossier, (
                f"Agent {agent} received a different dossier instance (expected `is` identity)"
            )

        # --- assertions: workflow completed with all 5 stages ---
        assert mock_execution.status == "completed"
        assert len(mock_execution.stages) == 5

    @pytest.mark.asyncio
    async def test_paper_review_workflow_handles_intermediate_stage_dossier_replacement(self):
        """Stage 2's dossier replaces None from stage 1 and reaches stages 3-5.

        Scenario:
          - Stage 1 (search-related-work): produces NO dossier
          - Stage 2 (review-paper): produces a NEW ResearchDossier
          - Stages 3-5: produce NO dossier

        Assert:
          - Stage 1 did NOT receive a dossier (current_dossier starts as None)
          - Stage 2 did NOT receive a dossier (current_dossier was still None)
          - Stages 3, 4, 5 receive stage 2's dossier (identity check)
          - Workflow completes successfully with all 5 stages
        """
        stage2_dossier = _make_dossier()

        # --- mock agents ---
        mock_scholar = MagicMock()
        mock_scholar.run = AsyncMock(return_value=_make_agent_result(
            "Search results found.",
            context={},  # no dossier from stage 1
        ))

        mock_reviewer = MagicMock()
        mock_reviewer.run = AsyncMock(return_value=_make_agent_result(
            "Review done.",
            context={"research_dossier": stage2_dossier, "rating": 7.5},
        ))

        mock_debater = MagicMock()
        mock_debater.run = AsyncMock(return_value=_make_agent_result("Debate done."))

        mock_writer1 = MagicMock()
        mock_writer1.run = AsyncMock(return_value=_make_agent_result("Refine done."))

        mock_writer2 = MagicMock()
        mock_writer2.run = AsyncMock(return_value=_make_agent_result("Editor done."))

        agents = [mock_scholar, mock_reviewer, mock_debater, mock_writer1, mock_writer2]

        # --- agent assignments ---
        assignments = {sid: str(uuid4()) for sid in STAGE_IDS}
        config = _make_config()
        config_map = {cid: config for cid in assignments.values()}

        async def mock_get_config(_db, _user_id, config_id):
            return config_map.get(str(config_id))

        agent_iter = iter(agents)

        def create_agent_side_effect(*_args, **_kwargs):
            return next(agent_iter)

        # --- mock DB session ---
        mock_execution = MagicMock()
        mock_execution.id = uuid4()
        mock_execution.stages = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = False

        # --- patch and run ---
        with (
            patch("app.api.routes.workflows.AsyncSessionLocal", return_value=mock_session_cm),
            patch("app.api.routes.workflows._get_user_config_by_id", side_effect=mock_get_config),
            patch("app.api.routes.workflows.create_agent", side_effect=create_agent_side_effect),
            patch("app.api.routes.workflows.fetch_model_pricing", new_callable=AsyncMock, return_value={}),
            patch("app.api.routes.workflows.calculate_cost", return_value=0.0),
            patch("app.api.routes.workflows.model_supports_pdf", return_value=False),
            patch("app.api.routes.workflows.evaluate_rubric", new_callable=AsyncMock, return_value=None),
            patch("app.api.routes.workflows._build_stage_context", side_effect=lambda orig, _find: orig),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            from app.api.routes.workflows import _run_workflow_background

            await _run_workflow_background(
                execution_id=str(uuid4()),
                user_id="test-user",
                workflow_id="paper-review",
                original_context="Test paper content",
                pdf_bytes=None,
                paper_s2_id=None,
                topic_query="test query",
                agent_assignments=assignments,
                paper_content=None,
                rubric_standard="general",
            )

        # --- assertions: stages 1 and 2 did NOT receive a dossier ---
        scholar_ctx = mock_scholar.run.call_args.kwargs["context"]
        assert "research_dossier" not in scholar_ctx, (
            "Stage 1 (scholar) should not receive a dossier when current_dossier starts as None"
        )

        reviewer_ctx = mock_reviewer.run.call_args.kwargs["context"]
        assert "research_dossier" not in reviewer_ctx, (
            "Stage 2 (reviewer) should not receive a dossier when stage 1 produced none"
        )

        # --- assertions: stages 3-5 received stage 2's dossier (identity) ---
        for agent in [mock_debater, mock_writer1, mock_writer2]:
            agent.run.assert_called_once()
            ctx = agent.run.call_args.kwargs["context"]
            assert "research_dossier" in ctx, (
                f"Agent {agent} did not receive research_dossier in context"
            )
            assert ctx["research_dossier"] is stage2_dossier, (
                f"Agent {agent} received wrong dossier (expected stage 2's dossier by identity)"
            )

        # --- assertions: workflow completed with all 5 stages ---
        assert mock_execution.status == "completed"
        assert len(mock_execution.stages) == 5
