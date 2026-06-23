"""FastAPI dependencies for the Academic Pal API."""

from typing import Annotated, Optional

from fastapi import HTTPException, Query, status

from app.core.security import decode_access_token


async def get_current_user_from_query(
    token: Annotated[Optional[str], Query()] = None,
) -> str:
    """Extract and validate a JWT from a query parameter.

    Intended for SSE endpoints where the browser ``EventSource`` API cannot set
    custom ``Authorization`` headers.  The client passes the access token as
    ``?token=<jwt>`` instead.

    Returns the ``user_id`` (the ``sub`` claim) on success.

    Raises ``HTTPException(401)`` when the token is missing, expired, malformed,
    or is not an ``access``-type token.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    return user_id
