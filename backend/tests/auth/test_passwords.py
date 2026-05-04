"""Sprint -0.5 — bcrypt password tests."""

from __future__ import annotations

from waraq.auth import hash_password, verify_password


class TestPasswordHashing:
    def test_hash_is_60_chars(self) -> None:
        h = hash_password("correct horse battery staple")
        assert len(h) == 60

    def test_hash_does_not_contain_plaintext(self) -> None:
        plain = "shibboleth"
        assert plain not in hash_password(plain)

    def test_hash_is_nondeterministic(self) -> None:
        # Same plaintext, two different salts → two different hashes.
        a = hash_password("same")
        b = hash_password("same")
        assert a != b

    def test_verify_correct_password(self) -> None:
        h = hash_password("hunter2")
        assert verify_password("hunter2", h) is True

    def test_verify_wrong_password(self) -> None:
        h = hash_password("hunter2")
        assert verify_password("hunter3", h) is False

    def test_verify_empty_against_real_hash(self) -> None:
        h = hash_password("non-empty")
        assert verify_password("", h) is False

    def test_verify_garbage_hash_returns_false(self) -> None:
        # Doesn't raise — auth service treats malformed hashes as wrong-password.
        assert verify_password("anything", "not a real bcrypt hash") is False

    def test_unicode_password_round_trip(self) -> None:
        plain = "بسم الله 🔐"
        h = hash_password(plain)
        assert verify_password(plain, h) is True
        assert verify_password(plain + " ", h) is False
