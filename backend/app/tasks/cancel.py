"""Redis-backed cancel flags for workflow execution cancellation."""

import logging

from app.core.database import redis_client

logger = logging.getLogger(__name__)

_CANCEL_PREFIX = "cancel:"
_CANCEL_TTL = 86400  # 24h auto-cleanup


async def set_cancel(execution_id: str, cancelled: bool = True) -> None:
    key = f"{_CANCEL_PREFIX}{execution_id}"
    if cancelled:
        await redis_client.set(key, "1")
        await redis_client.expire(key, _CANCEL_TTL)
    else:
        await redis_client.delete(key)


async def is_cancelled(execution_id: str | None) -> bool:
    if execution_id is None:
        return False
    key = f"{_CANCEL_PREFIX}{execution_id}"
    result = await redis_client.get(key)
    return result == "1"


async def clear_cancel(execution_id: str) -> None:
    key = f"{_CANCEL_PREFIX}{execution_id}"
    await redis_client.delete(key)


def cancel_key(execution_id: str) -> str:
    return f"{_CANCEL_PREFIX}{execution_id}"
