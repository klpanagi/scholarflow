"""LLM Provider Health Monitor Service.

Continuously monitors health of configured LLM providers and caches
status in Redis. Never raises exceptions — all failures are caught
and reported as unhealthy status.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Literal

import httpx
from sqlalchemy import select, distinct

from app.core.config import settings

logger = logging.getLogger(__name__)

# Health check interval in seconds
HEALTH_CHECK_INTERVAL = 60

# Redis key for health status
REDIS_KEY = "llm:health_status"

# Status types
ProviderStatus = Literal["healthy", "degraded", "unhealthy", "unknown"]


@dataclass
class ModelHealth:
    """Health status for a single model."""
    model: str
    status: ProviderStatus
    latency_ms: float | None = None
    error: str | None = None
    last_checked: float | None = None


@dataclass
class ProviderHealth:
    """Health status for a provider (all its models)."""
    provider: str
    status: ProviderStatus
    models: list[ModelHealth]
    last_checked: float
    api_reachable: bool = True


def _get_provider_config() -> dict[str, dict]:
    """Get provider configuration from settings."""
    return {
        "opencode": {
            "base_url": settings.OPENCODE_GO_API_BASE,
            "api_key": settings.OPENCODE_GO_API_KEY,
        },
        "opencode-zen": {
            "base_url": settings.OPENCODE_ZEN_API_BASE,
            "api_key": settings.OPENCODE_ZEN_API_KEY,
        },
        "openrouter": {
            "base_url": settings.OPENROUTER_API_BASE,
            "api_key": settings.OPENROUTER_API_KEY,
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key": settings.OPENAI_API_KEY,
        },
    }


# Free models available per provider (used as fallback when no AgentConfig is using a model)
FREE_MODELS: dict[str, list[str]] = {
    "openrouter": [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free",
    ],
}


async def _get_active_models() -> dict[str, set[str]]:
    """Query agent configs from DB to find which providers/models are actually in use."""
    from app.core.database import AsyncSessionLocal
    from app.models import AgentConfig

    active: dict[str, set[str]] = {}
    try:
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(
                    AgentConfig.provider,
                    AgentConfig.model,
                ).distinct()
            )
            for row in rows:
                provider = row[0]
                model = row[1]
                if provider and model:
                    active.setdefault(provider, set()).add(model)
    except Exception as e:
        logger.warning(f"Failed to query active models from DB: {e}")
    return active


async def _check_provider_connectivity(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
) -> tuple[bool, str | None]:
    """Verify provider API is reachable via GET /models.

    Returns (reachable, error_message). Does NOT send chat/embedding calls.
    """
    start = time.monotonic()
    try:
        resp = await client.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        latency = (time.monotonic() - start) * 1000

        if resp.status_code == 200:
            logger.debug(f"Provider connectivity check OK ({latency:.0f}ms)")
            return True, None
        elif resp.status_code in (401, 403):
            return False, "Authentication failed — check API key"
        elif resp.status_code == 429:
            return True, None  # API reachable, just rate-limited on /models
        else:
            return False, f"HTTP {resp.status_code}"
    except httpx.TimeoutException:
        return False, "Timeout connecting to provider"
    except Exception as e:
        return False, str(e)[:100]


async def _check_provider_health(
    provider_name: str,
    config: dict,
    active_models: set[str],
) -> ProviderHealth:
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "")

    if not api_key:
        return ProviderHealth(
            provider=provider_name,
            status="unknown",
            models=[],
            last_checked=time.time(),
            api_reachable=False,
        )

    if not active_models:
        return ProviderHealth(
            provider=provider_name,
            status="idle",
            models=[],
            last_checked=time.time(),
            api_reachable=True,
        )

    async with httpx.AsyncClient() as client:
        reachable, error = await _check_provider_connectivity(client, base_url, api_key)

    model_health = [
        ModelHealth(
            model=m,
            status="healthy" if reachable else "unhealthy",
            error=error if not reachable else None,
            last_checked=time.time(),
        )
        for m in active_models
    ]

    return ProviderHealth(
        provider=provider_name,
        status="healthy" if reachable else "unhealthy",
        models=model_health,
        last_checked=time.time(),
        api_reachable=reachable,
    )


async def check_all_providers() -> dict[str, ProviderHealth]:
    """Check health of providers that have API keys.

    Only models that are actually in use (referenced by a user AgentConfig)
    are checked. Providers with an API key but no active models are reported
    as "idle" rather than "unhealthy".
    """
    try:
        configs = _get_provider_config()
        active_models = await _get_active_models()

        results = {}
        for name, config in configs.items():
            api_key = config.get("api_key", "")
            if not api_key:
                continue
            models = active_models.get(name, set())
            if not models:
                results[name] = await _check_provider_health(name, config, set())
                continue
            try:
                results[name] = await _check_provider_health(name, config, models)
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = ProviderHealth(
                    provider=name,
                    status="unhealthy",
                    models=[],
                    last_checked=time.time(),
                    api_reachable=False,
                )
        return results
    except Exception as e:
        logger.error(f"Health check completely failed: {e}")
        return {}


async def get_cached_health() -> dict:
    """Get cached health status from Redis. Falls back to empty dict."""
    try:
        from app.core.database import redis_client
        data = await redis_client.get(REDIS_KEY)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Failed to read health cache: {e}")
    return {}


async def cache_health(health: dict[str, ProviderHealth]) -> None:
    """Cache health status in Redis."""
    try:
        from app.core.database import redis_client
        serializable = {
            name: asdict(provider) for name, provider in health.items()
        }
        await redis_client.set(
            REDIS_KEY,
            json.dumps(serializable),
            ex=HEALTH_CHECK_INTERVAL * 2,  # Expire after 2x check interval
        )
    except Exception as e:
        logger.warning(f"Failed to cache health status: {e}")


# Background task control
_health_task: asyncio.Task | None = None
_shutdown_event = asyncio.Event()


async def _health_check_loop():
    """Background loop that periodically checks provider health."""
    logger.info("LLM health monitor started")
    while not _shutdown_event.is_set():
        try:
            health = await check_all_providers()
            await cache_health(health)

            # Log status changes
            for name, provider in health.items():
                if provider.status == "unhealthy":
                    logger.warning(f"LLM provider '{name}' is unhealthy: {[m.error for m in provider.models if m.error]}")
                elif provider.status == "degraded":
                    logger.info(f"LLM provider '{name}' is degraded")
        except Exception as e:
            logger.error(f"Health check loop error: {e}")

        try:
            await asyncio.wait_for(_shutdown_event.wait(), timeout=HEALTH_CHECK_INTERVAL)
        except asyncio.TimeoutError:
            pass  # Normal timeout, continue checking

    logger.info("LLM health monitor stopped")


def start_health_monitor():
    """Start the background health monitoring task."""
    global _health_task
    if _health_task is None or _health_task.done():
        _shutdown_event.clear()
        _health_task = asyncio.create_task(_health_check_loop())
        logger.info("LLM health monitor task created")


def stop_health_monitor():
    """Stop the background health monitoring task."""
    _shutdown_event.set()
    logger.info("LLM health monitor stop requested")


# Singleton for direct health check (non-cached)
async def get_health_status() -> dict:
    """Get current health status. Returns cached if available, otherwise checks now."""
    cached = await get_cached_health()
    if cached:
        return cached

    # No cache — do a live check
    health = await check_all_providers()
    await cache_health(health)
    return {name: asdict(provider) for name, provider in health.items()}
