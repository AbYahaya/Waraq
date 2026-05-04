"""Auth service exceptions."""

from __future__ import annotations


class AuthError(Exception):
    """Base for auth-pipeline errors."""


class EmailAlreadyRegistered(AuthError):
    """Tried to register an account with an email already in use."""

    def __init__(self, *, email: str) -> None:
        super().__init__(f"Account with email {email!r} already exists")
        self.email = email


class InvalidCredentials(AuthError):
    """Authenticate called with an unknown email OR wrong password.

    Same exception class for both cases — never expose 'email exists but
    password wrong' vs 'email doesn't exist' to the caller (timing-safe
    against user enumeration)."""


class TokenInvalid(AuthError):
    """JWT verification failed (bad signature, malformed, wrong algorithm)."""


class TokenExpired(AuthError):
    """JWT signature was valid but the `exp` claim is in the past."""


class AccountInactive(AuthError):
    """Account exists and credentials match, but `active` is False."""

    def __init__(self, *, account_uuid: object) -> None:
        super().__init__(f"Account {account_uuid} is inactive")
        self.account_uuid = account_uuid
