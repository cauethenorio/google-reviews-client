"""Fernet encrypt/decrypt for OAuth token cookies."""

import json

from cryptography.fernet import Fernet, InvalidToken

TOKEN_COOKIE_NAME = "greviews_tokens"  # noqa: S105
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def encrypt_tokens(token_dict: dict, fernet: Fernet) -> str:
    """Encrypt a token dict into a cookie-safe string."""
    payload = json.dumps(token_dict).encode()
    return fernet.encrypt(payload).decode()


def decrypt_tokens(cookie_value: str, fernet: Fernet) -> dict | None:
    """Decrypt a cookie value back to a token dict. Returns None on any failure."""
    try:
        return json.loads(fernet.decrypt(cookie_value.encode()))
    except (InvalidToken, json.JSONDecodeError, Exception):
        return None
