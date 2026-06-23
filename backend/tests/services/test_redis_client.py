"""Tests for the Redis client accessor module."""

from unittest.mock import patch

import pytest
from redis.asyncio import Redis

from app.services.redis_client import get_redis


@pytest.mark.unit_db
def test_get_redis_returns_redis_instance():
    """``get_redis()`` returns an instance of ``redis.asyncio.Redis``."""
    client = get_redis()
    assert isinstance(client, Redis)


@pytest.mark.unit_db
def test_redis_client_has_decode_responses_true():
    """The shared client was created with ``decode_responses=True``."""
    client = get_redis()
    kwargs = client.connection_pool.connection_kwargs
    assert kwargs.get("decode_responses") is True


@pytest.mark.unit_db
def test_get_redis_is_singleton():
    """Multiple calls to ``get_redis()`` return the same object."""
    client_a = get_redis()
    client_b = get_redis()
    assert client_a is client_b


@pytest.mark.unit_db
def test_get_redis_connection_pool_configured():
    """The client's connection pool is configured from REDIS_URL."""
    client = get_redis()
    pool = client.connection_pool
    # The pool's ``connection_kwargs`` contain the decoded URL params.
    assert pool.connection_kwargs["host"] == "localhost"
    assert pool.connection_kwargs["port"] == 6379
    assert pool.connection_kwargs["db"] == 0
