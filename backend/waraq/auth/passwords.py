"""bcrypt password hashing.

Sprint -0.5 — keep the API surface tiny:
- hash_password(plain) → str (60-char bcrypt hash)
- verify_password(plain, stored_hash) → bool

bcrypt's `gensalt(rounds=12)` is the current default cost. Adjust when
hardware moves on; persisted hashes carry their cost factor inline so old
hashes verify correctly after a rounds bump.
"""

from __future__ import annotations

import bcrypt

_DEFAULT_ROUNDS = 12


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt. Returns the 60-char hash."""
    salt = bcrypt.gensalt(rounds=_DEFAULT_ROUNDS)
    hashed = bcrypt.hashpw(plain.encode("utf-8"), salt)
    return hashed.decode("ascii")


def verify_password(plain: str, stored_hash: str) -> bool:
    """Constant-time check of `plain` against `stored_hash`. Returns False
    rather than raising on malformed hashes — the auth service treats both
    cases as InvalidCredentials.
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), stored_hash.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return False
