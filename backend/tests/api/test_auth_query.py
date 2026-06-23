"""Tests for ``get_current_user_from_query`` JWT query-param dependency.

These are pure unit tests — no database required.  Every test creates a JWT
via ``create_access_token`` (or uses a deliberately invalid value) and asserts
that the dependency returns the expected ``user_id`` or raises ``401``.
"""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.security import create_access_token, create_refresh_token
from app.api.deps import get_current_user_from_query

pytestmark = pytest.mark.unit_db


class TestGetCurrentUserFromQuery:
    """Group tests for the query-param JWT dependency."""

    async def test_valid_jwt_query_param(self):
        """A valid access token with ``sub`` returns the user_id."""
        token = create_access_token({"sub": "test-user-id", "type": "access"})
        user_id = await get_current_user_from_query(token=token)
        assert user_id == "test-user-id"

    async def test_expired_jwt_raises_401(self):
        """An expired access token raises HTTP 401."""
        token = create_access_token(
            {"sub": "test-user-id"},
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(HTTPException) as exc:
            await get_current_user_from_query(token=token)
        assert exc.value.status_code == 401

    async def test_missing_jwt_raises_401(self):
        """An empty token string raises HTTP 401."""
        with pytest.raises(HTTPException) as exc:
            await get_current_user_from_query(token="")
        assert exc.value.status_code == 401

    async def test_malformed_jwt_raises_401(self):
        """A completely invalid JWT string raises HTTP 401."""
        with pytest.raises(HTTPException) as exc:
            await get_current_user_from_query(token="not-a-valid-token")
        assert exc.value.status_code == 401

    async def test_wrong_token_type_raises_401(self):
        """A refresh-type token (not access) raises HTTP 401."""
        token = create_refresh_token({"sub": "test-user-id"})
        with pytest.raises(HTTPException) as exc:
            await get_current_user_from_query(token=token)
        assert exc.value.status_code == 401

    async def test_missing_sub_claim_raises_401(self):
        """A token without a ``sub`` claim raises HTTP 401."""
        token = create_access_token({"type": "access"})
        with pytest.raises(HTTPException) as exc:
            await get_current_user_from_query(token=token)
        assert exc.value.status_code == 401
