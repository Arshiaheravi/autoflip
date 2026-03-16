"""
Unit tests for the auth service (password hashing, JWT, token decode).
These tests do NOT require MongoDB — they test pure logic only.
"""
import pytest
import sys
import os

# Make backend importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    safe_user,
)


# ──────────────────────────────────────────────────────────────────────────────
# Password hashing
# ──────────────────────────────────────────────────────────────────────────────
class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mypassword123")
        assert hashed != "mypassword123"

    def test_verify_correct_password(self):
        hashed = hash_password("correct_horse_battery")
        assert verify_password("correct_horse_battery", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct_horse_battery")
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self):
        """bcrypt uses random salt — two hashes of same pw must differ."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_verify_bad_hash_returns_false(self):
        assert verify_password("any", "not-a-valid-hash") is False


# ──────────────────────────────────────────────────────────────────────────────
# JWT
# ──────────────────────────────────────────────────────────────────────────────
class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token("user-123", "test@example.com")
        assert isinstance(token, str)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"

    def test_decode_invalid_token_returns_none(self):
        assert decode_token("invalid.token.here") is None

    def test_decode_empty_string_returns_none(self):
        assert decode_token("") is None

    def test_decode_tampered_token_returns_none(self):
        token = create_access_token("user-999", "flip@example.com")
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None


# ──────────────────────────────────────────────────────────────────────────────
# safe_user
# ──────────────────────────────────────────────────────────────────────────────
class TestSafeUser:
    def test_strips_password_hash(self):
        doc = {
            "id": "abc",
            "email": "a@b.com",
            "name": "Alice",
            "password_hash": "$2b$12$supersecret",
            "plan": "free",
            "created_at": "2025-01-01",
            "subscription_status": "inactive",
        }
        result = safe_user(doc)
        assert "password_hash" not in result
        assert result["id"] == "abc"
        assert result["email"] == "a@b.com"
        assert result["plan"] == "free"

    def test_defaults_for_missing_fields(self):
        result = safe_user({})
        assert result["plan"] == "free"
        assert result["subscription_status"] == "inactive"
