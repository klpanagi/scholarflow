import asyncio
import logging
import time
from typing import AsyncGenerator, Optional

import httpx
from langchain_openai import ChatOpenAI

from ..core.config import settings

logger = logging.getLogger(__name__)


_model_pricing_cache: dict[str, dict[str, float]] = {}
_pricing_cache_ts: float = 0.0
_PRICING_CACHE_TTL: float = 3600.0


def _build_pricing_index(raw: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Build a normalized lookup from OpenRouter pricing data.

    Stores both full model IDs (``xiaomi/mimo-v2.5``) and short names
    (``mimo-v2.5``) so callers can use either format.  Short-name keys
    are only added when they don't collide with an existing full ID.
    """
    index = dict(raw)
    for model_id, price in raw.items():
        short = model_id.split("/", 1)[-1] if "/" in model_id else model_id
        if short not in index:
            index[short] = price
    return index


async def fetch_model_pricing(force: bool = False) -> dict[str, dict[str, float]]:
    """Fetch per-model pricing from OpenRouter /api/v1/models.

    Returns a normalized lookup ``{model_key: {"input": $/token, "output": $/token}}``
    where keys include both full IDs and short names.  Cached for
    ``_PRICING_CACHE_TTL`` seconds.
    """
    global _model_pricing_cache, _pricing_cache_ts

    now = time.monotonic()
    if not force and _model_pricing_cache and (now - _pricing_cache_ts) < _PRICING_CACHE_TTL:
        return _model_pricing_cache

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get("https://openrouter.ai/api/v1/models")
            resp.raise_for_status()
            data = resp.json()

        raw: dict[str, dict[str, float]] = {}
        for m in data.get("data", []):
            model_id = m.get("id", "")
            p = m.get("pricing", {})
            prompt_price = float(p.get("prompt", 0) or 0)
            completion_price = float(p.get("completion", 0) or 0)
            if prompt_price < 0:
                prompt_price = 0.0
            if completion_price < 0:
                completion_price = 0.0
            raw[model_id] = {"input": prompt_price, "output": completion_price}

        _model_pricing_cache = _build_pricing_index(raw)
        _pricing_cache_ts = now
        logger.info(f"Loaded pricing for {len(raw)} models ({len(_model_pricing_cache)} keys) from OpenRouter")
        return _model_pricing_cache
    except Exception as e:
        logger.warning(f"Failed to fetch model pricing from OpenRouter: {e}")
        return _model_pricing_cache


def calculate_cost(model: str, input_tokens: int, output_tokens: int, pricing: dict | None = None) -> float:
    """Calculate cost in USD for a given model and token counts.

    Returns 0.0 if the model is not found (free/unknown).
    """
    p = (pricing or _model_pricing_cache).get(model, {})
    input_price = p.get("input", 0.0)
    output_price = p.get("output", 0.0)
    return input_tokens * input_price + output_tokens * output_price


PROVIDER_CONFIG = {
    "opencode": {
        "base_url": settings.OPENCODE_GO_API_BASE,
        "api_key": settings.OPENCODE_GO_API_KEY,
        "display_name": "OpenCode Go",
    },
    "opencode-zen": {
        "base_url": settings.OPENCODE_ZEN_API_BASE,
        "api_key": settings.OPENCODE_ZEN_API_KEY,
        "display_name": "OpenCode Zen",
    },
    "openrouter": {
        "base_url": settings.OPENROUTER_API_BASE,
        "api_key": settings.OPENROUTER_API_KEY,
        "display_name": "OpenRouter",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key": settings.OPENAI_API_KEY,
        "display_name": "OpenAI",
    },
}


def _get_provider_config(provider: str) -> dict:
    config = PROVIDER_CONFIG.get(provider)
    if not config:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(PROVIDER_CONFIG.keys())}")
    return config


async def get_completion(
    model: str,
    messages: list[dict],
    provider: str = "opencode",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    max_retries: int = 3,
) -> str:
    config = _get_provider_config(provider)
    base_url = config["base_url"].rstrip("/")
    api_key = config["api_key"]

    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code == 429:
                wait = 2 ** attempt * 2  # 2s, 4s, 8s
                logger.warning(f"[get_completion] 429 rate limit (attempt {attempt + 1}/{max_retries}), waiting {wait}s...")
                await asyncio.sleep(wait)
            else:
                raise
    raise last_error


async def get_embedding(
    model: str,
    texts: list[str],
    provider: str = "opencode",
) -> list[list[float]]:
    config = _get_provider_config(provider)
    base_url = config["base_url"].rstrip("/")
    api_key = config["api_key"]

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": texts,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]


async def _fetch_models_from_provider(provider: str) -> list[str]:
    config = _get_provider_config(provider)
    base_url = config["base_url"].rstrip("/")
    api_key = config["api_key"]

    if not api_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data", [])
            return sorted([m["id"] for m in models if "id" in m])
    except Exception:
        return []


async def get_available_models() -> dict[str, list[str]]:
    result = {}
    for provider in PROVIDER_CONFIG:
        models = await _fetch_models_from_provider(provider)
        result[provider] = models
    return result


# Curated embedding models per provider (not exposed via /models API)
EMBEDDING_MODELS: dict[str, list[str]] = {
    "opencode": [
        "text-embedding-3-small",
        "text-embedding-3-large",
        "text-embedding-ada-002",
    ],
    "opencode-zen": [
        "text-embedding-3-small",
        "text-embedding-3-large",
        "text-embedding-ada-002",
    ],
    "openrouter": [
        "openai/text-embedding-3-small",
        "openai/text-embedding-3-large",
        "openai/text-embedding-ada-002",
    ],
    "openai": [
        "text-embedding-3-small",
        "text-embedding-3-large",
        "text-embedding-ada-002",
    ],
}


async def get_available_embedding_models() -> dict[str, list[str]]:
    result = {}
    for provider, config in PROVIDER_CONFIG.items():
        if config.get("api_key"):
            result[provider] = EMBEDDING_MODELS.get(provider, [])
    return result


async def get_provider_status() -> dict[str, dict]:
    return {
        "opencode": {
            "configured": bool(settings.OPENCODE_GO_API_KEY),
            "api_base": settings.OPENCODE_GO_API_BASE,
        },
        "opencode-zen": {
            "configured": bool(settings.OPENCODE_ZEN_API_KEY),
            "api_base": settings.OPENCODE_ZEN_API_BASE,
        },
        "openrouter": {
            "configured": bool(settings.OPENROUTER_API_KEY),
            "api_base": settings.OPENROUTER_API_BASE,
        },
        "openai": {
            "configured": bool(settings.OPENAI_API_KEY),
            "api_base": "https://api.openai.com/v1",
        },
    }


class LLMService:

    def get_llm(
        self,
        model: str | None = None,
        provider: str = "opencode",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ChatOpenAI:
        """All providers use OpenAI-compatible APIs, so ChatOpenAI with custom base_url works for all."""
        config = _get_provider_config(provider)
        model = model or "opencode-1-mini"

        return ChatOpenAI(
            model=model,
            openai_api_key=config["api_key"],
            openai_api_base=config["base_url"],
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def get_completion(self, *args, **kwargs):
        return await get_completion(*args, **kwargs)

    async def get_embedding(self, *args, **kwargs):
        return await get_embedding(*args, **kwargs)

    async def get_available_models(self, *args, **kwargs):
        return await get_available_models(*args, **kwargs)

    async def get_available_embedding_models(self, *args, **kwargs):
        return await get_available_embedding_models(*args, **kwargs)

    async def get_provider_status(self, *args, **kwargs):
        return await get_provider_status(*args, **kwargs)


llm_service = LLMService()
