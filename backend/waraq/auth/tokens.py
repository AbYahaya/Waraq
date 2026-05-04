"""JWT issuance and verification.

Sprint -0.5 — single-claim tokens carrying the account_uuid in `sub`.
Expiry per `Settings.jwt_expiry_minutes`. HS256 with `Settings.jwt_secret`.

Scope (refresh tokens, revocation lists, scope claims, audience claims) is
deferred — auth scaffolding only.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from waraq.auth.exceptions import TokenExpired, TokenInvalid
from waraq.db.session import get_settings


@dataclass(frozen=True, slots=True)
class TokenPayload:
    account_uuid: _uuid.UUID
    issued_at: datetime
    expires_at: datetime


def issue_token(*, account_uuid: _uuid.UUID, now: datetime | None = None) -> str:
    """Issue a JWT for `account_uuid`. `now` is injectable for tests."""
    settings = get_settings()
    issued_at = now if now is not None else datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {
        "sub": str(account_uuid),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    encoded: str = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded


def verify_token(token: str) -> TokenPayload:
    """Verify `token`'s signature and expiry. Returns the parsed payload.

    Raises:
        TokenExpired: if `exp` is in the past.
        TokenInvalid: for any other failure (bad signature, malformed,
            wrong algorithm, missing/invalid sub).
    """
    settings = get_settings()
    try:
        decoded = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError as exc:
        raise TokenExpired("Token has expired") from exc
    except JWTError as exc:
        raise TokenInvalid(f"Token verification failed: {exc}") from exc

    sub = decoded.get("sub")
    if not isinstance(sub, str):
        raise TokenInvalid("Token missing or malformed `sub` claim")
    try:
        account_uuid = _uuid.UUID(sub)
    except ValueError as exc:
        raise TokenInvalid("Token `sub` is not a valid UUID") from exc

    iat = decoded.get("iat")
    exp = decoded.get("exp")
    if not isinstance(iat, int) or not isinstance(exp, int):
        raise TokenInvalid("Token missing iat/exp claims")

    return TokenPayload(
        account_uuid=account_uuid,
        issued_at=datetime.fromtimestamp(iat, tz=UTC),
        expires_at=datetime.fromtimestamp(exp, tz=UTC),
    )
