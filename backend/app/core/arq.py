"""ARQ connection pool and lifecycle management."""

import arq
from arq.connections import ArqRedis, RedisSettings

from app.core.config import settings

_arq_pool: ArqRedis | None = None


def get_arq_redis_settings() -> RedisSettings:
    return RedisSettings(
        host=str(settings.REDIS_URL.host or "localhost"),
        port=settings.REDIS_URL.port or 6379,
        database=1,
    )


async def get_arq_pool() -> ArqRedis:
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await arq.create_pool(get_arq_redis_settings())
    return _arq_pool


async def close_arq_pool() -> None:
    global _arq_pool
    if _arq_pool is not None:
        _arq_pool.close()  # type: ignore[reportUnusedCoroutine]
        _arq_pool = None


async def get_arq_pool_for_worker() -> ArqRedis:
    """Worker-specific pool without global caching."""
    return await arq.create_pool(get_arq_redis_settings())
