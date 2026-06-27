"""End-to-end tests for paper-review workflow variant dispatch.

Verifies that ``_run_stage()`` in ``backend/app/api/routes/workflows.py``
correctly forwards the ``variant`` field from ``AgentConfig`` to
``create_agent()``. This is the glue between the per-stage config
(debate variant choice) and the two-level agent registry
(SIMPLE/STANDARD/DEEP variants for ``AgentRole.DEBATER``).

The focus here is on variant propagation specifically — dossier
propagation is covered in ``test_paper_review_e2e.py``.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models import AgentRole, AgentVariant


def _make_config(role: AgentRole, variant: AgentVariant | None = None) -> MagicMock:
    """Create a mock agent config with a specific role and variant."""
    config = MagicMock()
    config.name = "test-agent"
    config.role = role
    config.model = "test-model"
    config.provider = "test-provider"
    config.strategy = MagicMock(value="direct")
    config.skills = []
    config.system_prompt = "Test system prompt"
    config.temperature = 0.7
    config.max_tokens = 4096
    config.variant = variant
    return config


def _make_agent_result(output: str, context: dict | None = None) -> dict:
    """Standard agent run result shape that ``_run_stage`` expects."""
    return {
        "output": output,
        "context": context or {},
        "metadata": {"usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}},
    }


class TestPaperReviewWorkflowVariantDispatch:
    """End-to-end tests for variant dispatch from config to factory."""

    @pytest.mark.asyncio
    @pytest.mark.unit_db
    async def test_paper_review_workflow_passes_deep_variant_to_factory(self):
        """When config has variant=DEEP, ``_run_stage`` passes variant="deep" to ``create_agent``.

        This is the critical wiring test for the debate variant feature:
          - ``AgentConfig.variant`` is set to ``AgentVariant.DEEP``
          - ``_run_stage()`` must extract its string value and pass it as
            the ``variant`` kwarg to ``create_agent()``
          - The factory's two-level registry then resolves DEBATER+deep
            to ``DeepDebateAgent`` (we don't instantiate the real class here —
            we only verify the dispatch plumbing)

        Scenario:
          - 4-stage paper-review workflow runs end-to-end
          - Stage 3 (debate-review) config has variant=DEEP
          - All other stages use a config with variant=None (non-DEBATER roles
            ignore the variant; DEBATER+None falls back to "simple")

        Assert:
          - ``create_agent`` was called with ``variant="deep"`` for stage 3
          - ``create_agent`` was called with ``variant=None`` for the other stages
        """
        def cfg_for(role: AgentRole) -> MagicMock:
            return _make_config(role=role, variant=AgentVariant.DEEP if role == AgentRole.DEBATER else None)

        mock_scholar = MagicMock()
        mock_scholar.run = AsyncMock(return_value=_make_agent_result("Search done."))

        mock_reviewer = MagicMock()
        mock_reviewer.run = AsyncMock(return_value=_make_agent_result("Review done."))

        mock_debater = MagicMock()
        mock_debater.run = AsyncMock(return_value=_make_agent_result("Debate done."))

        mock_writer = MagicMock()
        mock_writer.run = AsyncMock(return_value=_make_agent_result("Writer done."))

        agents = [mock_scholar, mock_reviewer, mock_debater, mock_writer]

        stage_ids = ["search-related-work", "review-paper", "debate-review", "paper-review-writer"]
        assignments = {sid: str(uuid4()) for sid in stage_ids}
        config_map = {
            assignments["search-related-work"]: cfg_for(AgentRole.RESEARCHER),
            assignments["review-paper"]: cfg_for(AgentRole.REVIEWER),
            assignments["debate-review"]: cfg_for(AgentRole.DEBATER),
            assignments["paper-review-writer"]: cfg_for(AgentRole.WRITER),
        }

        async def mock_get_config(_db, _user_id, config_id):
            return config_map.get(str(config_id))

        agent_iter = iter(agents)
        captured_calls: list[dict] = []

        def create_agent_side_effect(*args, **kwargs):
            captured_calls.append({"args": args, "kwargs": kwargs})
            return next(agent_iter)

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

        with (
            patch("app.api.routes.workflows.AsyncSessionLocal", return_value=mock_session_cm),
            patch("app.api.routes.workflows._get_user_config_by_id", side_effect=mock_get_config),
            patch("app.api.routes.workflows.create_agent", side_effect=create_agent_side_effect),
            patch("app.api.routes.workflows.fetch_model_pricing", new_callable=AsyncMock, return_value={}),
            patch("app.api.routes.workflows.calculate_cost", return_value=0.0),
            patch("app.api.routes.workflows.model_supports_pdf", return_value=False),
            patch("app.api.routes.workflows.evaluate_rubric", new_callable=AsyncMock, return_value=None),
            patch("app.api.routes.workflows._build_stage_context", side_effect=lambda orig, _find, **kw: orig),
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

        assert len(captured_calls) == 4, (
            f"Expected 4 create_agent calls (one per stage), got {len(captured_calls)}"
        )

        stage_role_in_order = [
            AgentRole.RESEARCHER,
            AgentRole.REVIEWER,
            AgentRole.DEBATER,
            AgentRole.WRITER,
        ]
        expected_variants = [None, None, "deep", None]

        for idx, (call, role, expected_variant) in enumerate(
            zip(captured_calls, stage_role_in_order, expected_variants, strict=True)
        ):
            actual_variant = call["kwargs"].get("variant")
            assert actual_variant == expected_variant, (
                f"Stage {idx} (role={role.value}): expected variant={expected_variant!r}, "
                f"got {actual_variant!r}. Full kwargs: {call['kwargs']}"
            )
            assert call["kwargs"].get("agent_type") == role.value, (
                f"Stage {idx}: agent_type mismatch — "
                f"expected {role.value!r}, got {call['kwargs'].get('agent_type')!r}"
            )

        debate_call = captured_calls[2]
        assert debate_call["kwargs"]["variant"] == "deep", (
            f"debate-review stage must receive variant='deep', "
            f"got {debate_call['kwargs']['variant']!r}"
        )
        assert debate_call["kwargs"]["agent_type"] == AgentRole.DEBATER.value
