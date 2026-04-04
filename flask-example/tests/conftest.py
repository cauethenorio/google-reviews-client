"""Shared test fixtures for the Flask demo app."""

import pytest
from app import create_app
from cookies import encrypt_tokens, TOKEN_COOKIE_NAME  # noqa: F401

TEST_ENV = {
    "GOOGLE_CLIENT_ID": "test-client-id",
    "GOOGLE_CLIENT_SECRET": "test-client-secret",
    "SECRET_KEY": "test-secret-key-for-testing",
}


@pytest.fixture()
def env_vars(monkeypatch):
    """Set all required env vars for testing."""
    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)


@pytest.fixture()
def app(env_vars):
    """Create application for testing."""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture()
def fernet(app):
    """Get the Fernet instance from the app."""
    return app.config["FERNET"]


@pytest.fixture()
def authenticated_cookie(fernet):
    """Create an encrypted cookie with authenticated status."""
    token_data = {
        "auth_status": "authenticated",
        "access_token": "fake-access-token",
        "refresh_token": "fake-refresh-token",
        "expiry": "2099-01-01T00:00:00",
    }
    return encrypt_tokens(token_data, fernet)


@pytest.fixture()
def pending_cookie(fernet):
    """Create an encrypted cookie with pending auth status."""
    pending_data = {
        "auth_status": "pending",
        "state": "test-state-value",
        "verifier": "test-verifier-value",
    }
    return encrypt_tokens(pending_data, fernet)
