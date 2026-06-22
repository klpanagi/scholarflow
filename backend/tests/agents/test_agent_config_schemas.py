"""Tests for AgentConfig Pydantic schemas — variant field validation."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import AgentConfigCreate, AgentConfigUpdate, AgentConfigResponse


@pytest.mark.unit_db
class TestAgentConfigVariant:
    """AgentConfigCreate variant field tests."""

    def test_agent_config_create_with_simple_variant(self):
        """Create AgentConfigCreate with variant='simple' succeeds."""
        config = AgentConfigCreate(
            name="test",
            role="debater",
            variant="simple",
        )
        assert config.variant == "simple"

    def test_agent_config_create_with_standard_variant(self):
        """Create AgentConfigCreate with variant='standard' succeeds."""
        config = AgentConfigCreate(
            name="test",
            role="debater",
            variant="standard",
        )
        assert config.variant == "standard"

    def test_agent_config_create_with_deep_variant(self):
        """Create AgentConfigCreate with variant='deep' succeeds."""
        config = AgentConfigCreate(
            name="test",
            role="debater",
            variant="deep",
        )
        assert config.variant == "deep"

    def test_agent_config_create_with_no_variant(self):
        """Create AgentConfigCreate without variant defaults to None."""
        config = AgentConfigCreate(
            name="test",
            role="debater",
        )
        assert config.variant is None

    def test_agent_config_create_with_invalid_variant(self):
        """Create AgentConfigCreate with invalid variant raises ValidationError."""
        with pytest.raises(ValidationError) as excinfo:
            AgentConfigCreate(
                name="test",
                role="debater",
                variant="invalid",
            )
        errors = excinfo.value.errors()
        assert any("variant" in e["loc"] for e in errors)

    def test_agent_config_update_with_variant(self):
        """AgentConfigUpdate with variant='deep' succeeds."""
        update = AgentConfigUpdate(variant="deep")
        assert update.variant == "deep"

    def test_agent_config_update_with_no_variant(self):
        """AgentConfigUpdate without variant stays None."""
        update = AgentConfigUpdate()
        assert update.variant is None

    def test_agent_config_response_includes_variant(self):
        """AgentConfigResponse includes variant in serialized output."""
        uid = uuid4()
        now = datetime.now()
        config = AgentConfigResponse(
            id=uid,
            user_id=uid,
            name="test",
            role="debater",
            variant="simple",
            created_at=now,
            updated_at=now,
        )
        data = config.model_dump()
        assert "variant" in data
        assert data["variant"] == "simple"
