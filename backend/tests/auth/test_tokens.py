"""Sprint -0.5 — JWT token tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from waraq.auth import (
    TokenExpired,
    TokenInvalid,
    issue_token,
    verify_token,
)
from waraq.identity import new_uuid


class TestTokenRoundTrip:
    def test_issue_and_verify_returns_account_uuid(self) -> None:
        account_uuid = new_uuid()
        token = issue_token(account_uuid=account_uuid)

        payload = verify_token(token)
        assert payload.account_uuid == account_uuid

    def test_issued_at_and_expires_at_are_set(self) -> None:
        before = datetime.now(UTC) - timedelta(seconds=1)
        token = issue_token(account_uuid=new_uuid())
        after = datetime.now(UTC) + timedelta(seconds=1)

        payload = verify_token(token)
        assert before <= payload.issued_at <= after
        assert payload.expires_at > payload.issued_at


class TestTokenExpiry:
    def test_expired_token_raises_token_expired(self) -> None:
        # Issue with `now` 25 hours ago — exceeds the 24h default expiry.
        long_ago = datetime.now(UTC) - timedelta(hours=25)
        token = issue_token(account_uuid=new_uuid(), now=long_ago)

        with pytest.raises(TokenExpired):
            verify_token(token)


class TestTokenTampering:
    def test_garbage_token_raises_token_invalid(self) -> None:
        with pytest.raises(TokenInvalid):
            verify_token("not.a.real.jwt")

    def test_tampered_signature_raises_token_invalid(self) -> None:
        token = issue_token(account_uuid=new_uuid())
        # Flip the last char of the signature.
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with pytest.raises(TokenInvalid):
            verify_token(tampered)

    def test_unsigned_jwt_raises_token_invalid(self) -> None:
        # Algorithm mismatch — header says alg=none, our decode requires HS256.
        from base64 import urlsafe_b64encode

        def b64(s: bytes) -> str:
            return urlsafe_b64encode(s).rstrip(b"=").decode("ascii")

        header = b64(b'{"alg":"none","typ":"JWT"}')
        payload = b64(b'{"sub":"00000000-0000-0000-0000-000000000000","iat":1,"exp":9999999999}')
        unsigned = f"{header}.{payload}."
        with pytest.raises(TokenInvalid):
            verify_token(unsigned)
