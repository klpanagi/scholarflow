import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.core.database import get_db
from app.services import llm_service
from app.services.system_settings import get_setting, set_setting
from app.services.health_monitor import get_health_status, check_all_providers
from app.services.user_api_keys import get_user_api_key, set_user_api_key, delete_user_api_key, list_user_api_keys
from dataclasses import asdict

router = APIRouter(prefix="/settings", tags=["settings"])


class ProviderConfig(BaseModel):
    api_key: Optional[str] = None
    api_base: Optional[str] = None


class UpdateProviderRequest(BaseModel):
    provider: str
    config: ProviderConfig


class EmbeddingConfig(BaseModel):
    provider: str
    model: str


async def _get_embedding_config(db: AsyncSession) -> tuple[str, str]:
    db_provider = await get_setting(db, "embedding_provider")
    db_model = await get_setting(db, "embedding_model")
    return (db_provider or settings.EMBEDDING_PROVIDER, db_model or settings.EMBEDDING_MODEL)


@router.get("/providers")
async def get_providers(current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    status = await llm_service.get_provider_status()
    models = await llm_service.get_available_models()
    embedding_models = await llm_service.get_available_embedding_models()
    emb_provider, emb_model = await _get_embedding_config(db)

    return {
        "providers": status,
        "models": models,
        "embedding_models": embedding_models,
        "embedding_provider": emb_provider,
        "embedding_model": emb_model,
    }


@router.post("/embedding")
async def update_embedding_config(
    body: EmbeddingConfig,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await set_setting(db, "embedding_provider", body.provider)
    await set_setting(db, "embedding_model", body.model)
    return {"embedding_provider": body.provider, "embedding_model": body.model}


@router.get("/providers/{provider}/models")
async def get_provider_models(
    provider: str,
    current_user: str = Depends(get_current_user),
):
    models = await llm_service.get_available_models()
    if provider not in models:
        raise HTTPException(status_code=404, detail=f"Provider {provider} not found")
    return {"provider": provider, "models": models[provider]}


@router.post("/providers/test")
async def test_provider(
    provider: str,
    current_user: str = Depends(get_current_user),
):
    from app.services.health_monitor import FREE_MODELS

    status = await llm_service.get_provider_status()
    if provider not in status:
        raise HTTPException(status_code=404, detail=f"Provider {provider} not found")
    
    if not status[provider]["configured"]:
        return {"provider": provider, "status": "not_configured", "message": "API key not set"}
    
    try:
        free = FREE_MODELS.get(provider, [])
        if free:
            model = free[0]
        else:
            models = await llm_service.get_available_models()
            provider_models = models.get(provider, [])
            if not provider_models:
                return {"provider": provider, "status": "error", "message": "No models available"}
            model = provider_models[0]
        
        response = await asyncio.wait_for(
            llm_service.get_completion(
                model=model,
                messages=[{"role": "user", "content": "Say 'test successful' in 3 words."}],
                provider=provider,
                max_tokens=20,
            ),
            timeout=15,
        )
        return {"provider": provider, "status": "connected", "response": response, "model": model}
    except asyncio.TimeoutError:
        return {"provider": provider, "status": "error", "message": "Connection timed out (15s)"}
    except Exception as e:
        return {"provider": provider, "status": "error", "message": str(e)}


@router.get("/health")
async def get_llm_health(current_user: str = Depends(get_current_user)):
    health = await get_health_status()
    return {"providers": health}


@router.post("/health/check")
async def force_health_check(current_user: str = Depends(get_current_user)):
    health = await check_all_providers()
    from app.services.health_monitor import cache_health
    await cache_health(health)
    return {"providers": {name: asdict(p) for name, p in health.items()}}


class UserApiKeyRequest(BaseModel):
    service: str
    api_key: str


@router.get("/api-keys")
async def list_api_keys(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_user_api_keys(db, current_user)


@router.post("/api-keys")
async def save_api_key(
    body: UserApiKeyRequest,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed_services = {"semantic_scholar", "crossref", "openai", "openrouter", "openalex"}
    if body.service not in allowed_services:
        raise HTTPException(status_code=400, detail=f"Unknown service: {body.service}")
    await set_user_api_key(db, current_user, body.service, body.api_key)
    return {"service": body.service, "status": "saved"}


@router.delete("/api-keys/{service}")
async def remove_api_key(
    service: str,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_user_api_key(db, current_user, service)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No API key found for service: {service}")
    return {"service": service, "status": "deleted"}
