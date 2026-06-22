"""Tests for the AgentVariant enum."""

import pytest

from app.models import AgentVariant


@pytest.mark.unit_db
class TestAgentVariantValues:
    """AgentVariant enum has exactly 3 values with correct string mapping."""

    def test_agent_variant_values(self):
        """AgentVariant enum has exactly 3 expected members."""
        expected_values = {
            "SIMPLE": "simple",
            "STANDARD": "standard",
            "DEEP": "deep",
        }
        assert len(AgentVariant) == len(expected_values)
        for name, value in expected_values.items():
            member = getattr(AgentVariant, name)
            assert member.value == value
            assert member.name == name

    def test_agent_variant_string(self):
        """AgentVariant can be used as a string (== comparison works, .value returns the value)."""
        assert AgentVariant.SIMPLE == "simple"
        assert AgentVariant.STANDARD == "standard"
        assert AgentVariant.DEEP == "deep"
        assert AgentVariant.SIMPLE.value == "simple"
        assert AgentVariant.STANDARD.value == "standard"
        assert AgentVariant.DEEP.value == "deep"
