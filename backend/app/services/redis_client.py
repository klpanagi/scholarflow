"""Redis client accessor module.

Re-exports the shared async Redis client initialized in ``app.core.database``
so that callers can import ``get_redis`` explicitly rather than reaching into
the database module.

Usage::

    from app.services.redis_client import get_redis

    redis = get_redis()
    await redis.set("key", "value")
"""

from redis.asyncio import Redis

from app.core.database import redis_client


def get_redis() -> Redis:
    """Return the shared async Redis client instance.

    The client was initialised in :func:`app.core.database` on module import
    via ``aioredis.from_url(settings.REDIS_URL, decode_responses=True)``.
    """
    return redis_client
