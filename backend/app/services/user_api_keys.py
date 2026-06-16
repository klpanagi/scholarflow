import base64
import hashlib
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserApiKey
from app.core.config import settings


def _derive_key(user_id: str) -> bytes:
    return hashlib.sha256(f"{settings.SECRET_KEY}:{user_id}".encode()).digest()


def encrypt_api_key(plaintext: str, user_id: str) -> str:
    from cryptography.fernet import Fernet
    key = base64.urlsafe_b64encode(_derive_key(user_id))
    return Fernet(key).encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str, user_id: str) -> str:
    from cryptography.fernet import Fernet
    key = base64.urlsafe_b64encode(_derive_key(user_id))
    return Fernet(key).decrypt(ciphertext.encode()).decode()


async def get_user_api_key(db: AsyncSession, user_id: str, service: str) -> Optional[str]:
    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == UUID(user_id) if isinstance(user_id, str) else UserApiKey.user_id == user_id,
            UserApiKey.service == service,
            UserApiKey.is_active == True,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        return None
    return decrypt_api_key(row.api_key_encrypted, str(user_id))


async def set_user_api_key(db: AsyncSession, user_id: str, service: str, api_key: str) -> None:
    uid = UUID(user_id) if isinstance(user_id, str) else user_id
    existing = await db.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == uid,
            UserApiKey.service == service,
        )
    )
    row = existing.scalar_one_or_none()
    encrypted = encrypt_api_key(api_key, str(user_id))
    if row:
        row.api_key_encrypted = encrypted
        row.is_active = True
    else:
        db.add(UserApiKey(
            user_id=uid,
            service=service,
            api_key_encrypted=encrypted,
        ))
    await db.flush()


async def delete_user_api_key(db: AsyncSession, user_id: str, service: str) -> bool:
    uid = UUID(user_id) if isinstance(user_id, str) else user_id
    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == uid,
            UserApiKey.service == service,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        return False
    await db.delete(row)
    await db.flush()
    return True


async def list_user_api_keys(db: AsyncSession, user_id: str) -> list[dict]:
    uid = UUID(user_id) if isinstance(user_id, str) else user_id
    result = await db.execute(
        select(UserApiKey).where(UserApiKey.user_id == uid)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "service": r.service,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
