from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import SystemSetting


async def get_setting(db: AsyncSession, key: str) -> Optional[str]:
    result = await db.execute(select(SystemSetting.value).where(SystemSetting.key == key))
    row = result.scalar_one_or_none()
    return row


async def set_setting(db: AsyncSession, key: str, value: str) -> None:
    existing = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    row = existing.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
    await db.flush()
