"""FastAPI dependency providers.

- `get_db_session`: per-request async SQLAlchemy session, transactional —
  commits on success, rolls back on exception.
- `get_current_account`: extracts a JWT from the `Authorization: Bearer ...`
  header, verifies it, and resolves to an `Account`. Raises 401 on any
  failure (no leakage between unknown / inactive / expired).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.auth import (
    AuthError,
    TokenExpired,
    TokenInvalid,
    get_account_by_uuid,
    verify_token,
)
from waraq.db.session import _sessionmaker
from waraq.schemas import Account


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Per-request session. Commits on clean exit; rolls back on exception."""
    async with _sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return parts[1].strip()


async def get_current_account(
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> Account:
    """Resolve the current Account from the Bearer token. 401 on any failure."""
    token = _bearer_token(authorization)
    try:
        payload = verify_token(token)
    except TokenExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (TokenInvalid, AuthError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    account = await get_account_by_uuid(session=session, account_uuid=payload.account_uuid)
    if account is None or not account.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is unknown or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return account


CurrentAccount = Annotated[Account, Depends(get_current_account)]
