"""Shared test fixtures for the Flask demo app."""

import pytest
from app import create_app

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
