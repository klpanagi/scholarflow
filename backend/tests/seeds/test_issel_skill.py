"""Structural tests for the ISSEL paper review skill seed.

Tests that the ``issel-paper-review`` skill and ``ISSEL Paper Reviewer``
AgentConfig seeds defined in ``app.seeds.scholarflow_skills`` have the
correct structural attributes. Pure unit checks: no DB, no mocks.
"""

import pytest

from app.seeds.scholarflow_skills import _SKILL_SEEDS, _AGENT_SEEDS
from app.models import AgentRole, Strategy


class TestISSELSkillSeed:
    """Structural tests for the ISSEL paper review skill seed."""

    @pytest.mark.unit_db
    def test_skill_exists(self):
        names = [s["name"] for s in _SKILL_SEEDS]
        assert "issel-paper-review" in names

    @pytest.mark.unit_db
    def test_skill_is_private(self):
        skill = next(s for s in _SKILL_SEEDS if s["name"] == "issel-paper-review")
        assert skill["is_public"] is False

    @pytest.mark.unit_db
    def test_skill_has_no_tools(self):
        skill = next(s for s in _SKILL_SEEDS if s["name"] == "issel-paper-review")
        assert skill["builtin_tools"] == []

    @pytest.mark.unit_db
    def test_skill_has_prompt_template(self):
        skill = next(s for s in _SKILL_SEEDS if s["name"] == "issel-paper-review")
        assert len(skill["prompt_template"]) > 100
        prompt = skill["prompt_template"]
        # Should contain key criteria terms
        assert "innovation" in prompt.lower() or "novel" in prompt.lower()
        assert "methodology" in prompt.lower()
        assert "evaluation" in prompt.lower()

    @pytest.mark.unit_db
    def test_skill_has_required_keys(self):
        skill = next(s for s in _SKILL_SEEDS if s["name"] == "issel-paper-review")
        required = {"name", "description", "builtin_tools", "tags", "is_public", "prompt_template"}
        assert required.issubset(skill.keys())


class TestISSELAgentConfigSeed:
    """Structural tests for the ISSEL Paper Reviewer agent config seed."""

    @pytest.mark.unit_db
    def test_agent_exists(self):
        names = [a["name"] for a in _AGENT_SEEDS]
        assert "ISSEL Paper Reviewer" in names

    @pytest.mark.unit_db
    def test_agent_has_reviewer_role(self):
        agent = next(a for a in _AGENT_SEEDS if a["name"] == "ISSEL Paper Reviewer")
        assert agent["role"] == AgentRole.REVIEWER

    @pytest.mark.unit_db
    def test_agent_has_critique_strategy(self):
        agent = next(a for a in _AGENT_SEEDS if a["name"] == "ISSEL Paper Reviewer")
        assert agent["strategy"] == Strategy.CRITIQUE

    @pytest.mark.unit_db
    def test_agent_references_issel_skill(self):
        agent = next(a for a in _AGENT_SEEDS if a["name"] == "ISSEL Paper Reviewer")
        assert "issel-paper-review" in agent["skill_names"]

    @pytest.mark.unit_db
    def test_agent_has_no_variant(self):
        agent = next(a for a in _AGENT_SEEDS if a["name"] == "ISSEL Paper Reviewer")
        assert agent.get("variant") is None

    @pytest.mark.unit_db
    def test_agent_has_required_keys(self):
        agent = next(a for a in _AGENT_SEEDS if a["name"] == "ISSEL Paper Reviewer")
        required = {"name", "role", "provider", "model", "strategy", "system_prompt", "skill_names"}
        assert required.issubset(agent.keys())


class TestExistingSeedsUnchanged:
    """Regression tests ensuring existing seeds are not modified."""

    @pytest.mark.unit_db
    def test_existing_skills_count(self):
        assert len(_SKILL_SEEDS) == 11  # 10 original + 1 ISSEL

    @pytest.mark.unit_db
    def test_existing_agent_count(self):
        assert len(_AGENT_SEEDS) == 14

    @pytest.mark.unit_db
    def test_paper_review_skill_unchanged(self):
        skill = next(s for s in _SKILL_SEEDS if s["name"] == "paper-review")
        assert skill["is_public"] is True
        assert skill["builtin_tools"] == []

    @pytest.mark.unit_db
    def test_solo_paper_review_skill_unchanged(self):
        skill = next(s for s in _SKILL_SEEDS if s["name"] == "solo-paper-review")
        assert skill["is_public"] is True
        assert "search_papers" in skill["builtin_tools"]

    @pytest.mark.unit_db
    def test_proposal_reviewer_agent_unchanged(self):
        agent = next(a for a in _AGENT_SEEDS if a["name"] == "Proposal Reviewer")
        assert agent["role"] == AgentRole.REVIEWER
        assert "solo-paper-review" in agent["skill_names"]
