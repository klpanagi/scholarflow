"""Shared FastAPI dependencies for route handlers.

Consolidates frequently-duplicated patterns like user lookup so every
route module doesn't re-implement the same ``_get_user`` function.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_user(user_id: str, db: AsyncSession) -> User:
    """Fetch the current user by ID, raising 401 if the record is missing.

    All authenticated routes should use this to ensure the user exists
    in the database.  A JWT can be valid while the corresponding User row
    has been deleted, so this check prevents confusing 500 errors.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_user_optional(user_id: str, db: AsyncSession) -> User | None:
    """Fetch the current user by ID, returning ``None`` when missing.

    Use this in dashboard-style endpoints where missing users should
    return empty data rather than an error.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
