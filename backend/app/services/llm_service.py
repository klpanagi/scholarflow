from typing import AsyncGenerator, Optional

import httpx
from langchain_openai import ChatOpenAI

from ..core.config import settings


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
) -> str:
    config = _get_provider_config(provider)
    base_url = config["base_url"].rstrip("/")
    api_key = config["api_key"]

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
