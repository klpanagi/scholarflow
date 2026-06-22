"""Unit tests for variant-based dispatch in the agent factory (Task 5).

Verifies that ``AGENT_REGISTRY`` supports a two-level (role → variant → class)
structure for the ``debater`` role, while keeping a flat class reference for
all other roles. ``create_agent()`` must accept a ``variant`` keyword argument
and resolve the correct debate agent class. For non-debater roles the
``variant`` argument is ignored — preserving backward compatibility.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.agents.factory import AGENT_REGISTRY, create_agent, list_agents


# Required because conftest's autouse ``clean_db`` fixture tries to acquire
# a DB engine that is not running in CI.
pytestmark = pytest.mark.unit_db


class TestAgentRegistryStructure:
    def test_agent_registry_has_debater_dict(self):
        assert "debater" in AGENT_REGISTRY
        assert isinstance(AGENT_REGISTRY["debater"], dict), (
            "AGENT_REGISTRY['debater'] must be a dict for variant dispatch, "
            f"got {type(AGENT_REGISTRY['debater']).__name__}"
        )

    def test_debater_registry_has_three_variants(self):
        variants = AGENT_REGISTRY["debater"]
        assert set(variants.keys()) == {"simple", "standard", "deep"}, (
            f"debater must have exactly simple/standard/deep variants, "
            f"got {set(variants.keys())}"
        )

    def test_debater_simple_maps_to_simple_debate_agent(self):
        from app.agents.simple_debate_agent import SimpleDebateAgent

        assert AGENT_REGISTRY["debater"]["simple"] is SimpleDebateAgent

    def test_debater_standard_maps_to_debate_agent(self):
        from app.agents.debate_agent import DebateAgent

        assert AGENT_REGISTRY["debater"]["standard"] is DebateAgent

    def test_debater_deep_maps_to_deep_debate_agent(self):
        from app.agents.deep_debate_agent import DeepDebateAgent

        assert AGENT_REGISTRY["debater"]["deep"] is DeepDebateAgent


class TestCreateAgentDebaterDispatch:
    def test_create_agent_debater_simple(self, mock_llm):
        from app.agents.simple_debate_agent import SimpleDebateAgent

        with patch("app.agents.factory.llm_service.get_llm", return_value=mock_llm):
            agent = create_agent(agent_type="debater", variant="simple")
        assert isinstance(agent, SimpleDebateAgent), (
            f"Expected SimpleDebateAgent, got {type(agent).__name__}"
        )

    def test_create_agent_debater_standard(self, mock_llm):
        from app.agents.debate_agent import DebateAgent

        with patch("app.agents.factory.llm_service.get_llm", return_value=mock_llm):
            agent = create_agent(agent_type="debater", variant="standard")
        assert isinstance(agent, DebateAgent), (
            f"Expected DebateAgent, got {type(agent).__name__}"
        )

    def test_create_agent_debater_deep(self, mock_llm):
        from app.agents.deep_debate_agent import DeepDebateAgent

        with patch("app.agents.factory.llm_service.get_llm", return_value=mock_llm):
            agent = create_agent(agent_type="debater", variant="deep")
        assert isinstance(agent, DeepDebateAgent), (
            f"Expected DeepDebateAgent, got {type(agent).__name__}"
        )

    def test_create_agent_debater_default_variant(self, mock_llm):
        from app.agents.simple_debate_agent import SimpleDebateAgent

        with patch("app.agents.factory.llm_service.get_llm", return_value=mock_llm):
            agent = create_agent(agent_type="debater")
        assert isinstance(agent, SimpleDebateAgent), (
            f"Default variant must be SimpleDebateAgent, got {type(agent).__name__}"
        )

    def test_create_agent_debater_unknown_variant(self, mock_llm):
        with patch("app.agents.factory.llm_service.get_llm", return_value=mock_llm):
            with pytest.raises(ValueError) as exc_info:
                create_agent(agent_type="debater", variant="bogus")
        msg = str(exc_info.value).lower()
        assert "bogus" in msg, f"Error must mention 'bogus', got: {exc_info.value}"
        for variant in ("simple", "standard", "deep"):
            assert variant in msg, (
                f"Error must list available variant '{variant}', got: {exc_info.value}"
            )


class TestCreateAgentNonDebaterCompat:
    def test_create_agent_non_debater_no_variant_arg(self, mock_llm):
        from app.agents.search_agent import SearchAgent

        with patch("app.agents.factory.llm_service.get_llm", return_value=mock_llm):
            agent = create_agent(agent_type="researcher")
        assert isinstance(agent, SearchAgent), (
            f"Expected SearchAgent, got {type(agent).__name__}"
        )

    def test_create_agent_non_debater_with_variant_ignored(self, mock_llm):
        from app.agents.search_agent import SearchAgent

        with patch("app.agents.factory.llm_service.get_llm", return_value=mock_llm):
            agent = create_agent(agent_type="researcher", variant="simple")
        assert isinstance(agent, SearchAgent), (
            f"Expected SearchAgent, got {type(agent).__name__}"
        )


class TestListAgentsVariants:
    def test_list_agents_includes_all_variants(self):
        entries = list_agents()
        assert isinstance(entries, list), f"Expected list, got {type(entries)}"
        for entry in entries:
            assert isinstance(entry, dict), f"Entry must be dict, got {entry!r}"
            assert "name" in entry, f"Entry must have 'name', got {entry!r}"
            assert "description" in entry, f"Entry must have 'description', got {entry!r}"
        names = {entry["name"] for entry in entries}
        for variant in ("simple", "standard", "deep"):
            assert any(
                name.startswith("debater") and variant in name for name in names
            ), (
                f"list_agents() must include a debater:{variant} entry, "
                f"got names: {names}"
            )
        # Threshold is 4: 1 debater flat role is replaced by 3 variants, so
        # the spec requires at least 3 debater entries + 1 other role entry.
        # We use >= 4 to stay resilient to future flat-role additions.
        assert len(entries) >= 4, (
            f"list_agents() must include all variants, got {len(entries)} entries"
        )
