"""Tests for app factory and env var validation (INFRA-01)."""

import pytest
from app import create_app
from cryptography.fernet import Fernet

REQUIRED_VARS = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "SECRET_KEY"]


class TestCreateAppSuccess:
    """Test that app creates successfully with all env vars set."""

    def test_create_app_success(self, app):
        """App is created and configured correctly."""
        assert app is not None
        assert isinstance(app.config["FERNET"], Fernet)
        assert app.config["GOOGLE_CLIENT_ID"] == "test-client-id"
        assert app.config["GOOGLE_CLIENT_SECRET"] == "test-client-secret"

    def test_fernet_key_is_deterministic(self, env_vars):
        """Same SECRET_KEY produces identical Fernet instances."""
        app1 = create_app()
        app2 = create_app()
        # Encrypt with one, decrypt with the other
        plaintext = b"test-payload"
        encrypted = app1.config["FERNET"].encrypt(plaintext)
        assert app2.config["FERNET"].decrypt(encrypted) == plaintext


class TestMissingEnvVars:
    """Test that missing env vars raise RuntimeError."""

    def _clear_all(self, monkeypatch):
        """Remove all required env vars."""
        for var in REQUIRED_VARS:
            monkeypatch.delenv(var, raising=False)

    def test_missing_google_client_id(self, monkeypatch):
        """Missing GOOGLE_CLIENT_ID raises RuntimeError."""
        self._clear_all(monkeypatch)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_ID"):
            create_app()

    def test_missing_google_client_secret(self, monkeypatch):
        """Missing GOOGLE_CLIENT_SECRET raises RuntimeError."""
        self._clear_all(monkeypatch)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-id")
        with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_SECRET"):
            create_app()

    def test_missing_secret_key(self, monkeypatch):
        """Missing SECRET_KEY raises RuntimeError."""
        self._clear_all(monkeypatch)
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            create_app()

    def test_missing_var_error_says_not_set(self, monkeypatch):
        """Error message includes 'not set'."""
        self._clear_all(monkeypatch)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        with pytest.raises(RuntimeError, match="not set"):
            create_app()
