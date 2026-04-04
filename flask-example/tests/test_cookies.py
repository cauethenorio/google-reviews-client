"""Tests for cookie encryption round-trip and failure cases (INFRA-02)."""

from cookies import COOKIE_MAX_AGE, TOKEN_COOKIE_NAME, decrypt_tokens, encrypt_tokens
from cryptography.fernet import Fernet


class TestEncryptDecrypt:
    """Test encrypt/decrypt round-trip and edge cases."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted tokens decrypt back to the original dict."""
        fernet = Fernet(Fernet.generate_key())
        token_dict = {
            "access_token": "ya29.xxx",
            "refresh_token": "1//xxx",
            "expiry": "2026-01-01T00:00:00Z",
        }
        encrypted = encrypt_tokens(token_dict, fernet)
        result = decrypt_tokens(encrypted, fernet)
        assert result == token_dict

    def test_encrypt_returns_string(self):
        """encrypt_tokens returns a string."""
        fernet = Fernet(Fernet.generate_key())
        result = encrypt_tokens({"key": "value"}, fernet)
        assert isinstance(result, str)

    def test_decrypt_invalid_returns_none(self):
        """Invalid encrypted data returns None."""
        fernet = Fernet(Fernet.generate_key())
        result = decrypt_tokens("not-valid-encrypted-data", fernet)
        assert result is None

    def test_decrypt_tampered_returns_none(self):
        """Tampered encrypted data returns None."""
        fernet = Fernet(Fernet.generate_key())
        encrypted = encrypt_tokens({"access_token": "ya29.xxx"}, fernet)
        # Tamper with the last character
        tampered = encrypted[:-1] + ("A" if encrypted[-1] != "A" else "B")
        result = decrypt_tokens(tampered, fernet)
        assert result is None

    def test_decrypt_wrong_key_returns_none(self):
        """Decrypting with a different key returns None."""
        fernet1 = Fernet(Fernet.generate_key())
        fernet2 = Fernet(Fernet.generate_key())
        encrypted = encrypt_tokens({"access_token": "ya29.xxx"}, fernet1)
        result = decrypt_tokens(encrypted, fernet2)
        assert result is None


class TestCookieConstants:
    """Test cookie configuration constants."""

    def test_token_cookie_name(self):
        """Cookie name is set correctly."""
        assert TOKEN_COOKIE_NAME == "greviews_tokens"

    def test_cookie_max_age(self):
        """Cookie max age is 7 days in seconds."""
        assert COOKIE_MAX_AGE == 604800
