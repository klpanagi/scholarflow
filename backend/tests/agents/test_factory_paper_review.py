"""Regression tests for PaperReviewAgent factory registration.

Verifies that PaperReviewAgent is properly registered in the AGENT_REGISTRY
and can be created via the factory function. See Task 12 of scholar-agent-improvement plan.
"""

from unittest.mock import patch

from app.agents.factory import AGENT_REGISTRY, create_agent
from app.agents.paper_review_agent import PaperReviewAgent


class TestPaperReviewFactoryRegistration:
    """Verify PaperReviewAgent is registered in the factory."""

    def test_reviewer_in_registry(self):
        """AGENT_REGISTRY["reviewer"] must be the PaperReviewAgent class."""
        assert "reviewer" in AGENT_REGISTRY
        assert AGENT_REGISTRY["reviewer"] is PaperReviewAgent

    def test_create_agent_reviewer(self, mock_llm):
        """create_agent("reviewer") must return a PaperReviewAgent instance."""
        with patch("app.agents.factory.llm_service.get_llm", return_value=mock_llm):
            agent = create_agent(agent_type="reviewer")
        assert isinstance(agent, PaperReviewAgent)
