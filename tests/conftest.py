"""Shared pytest fixtures for google-reviews-client tests."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from google_reviews_client.cli.config import Config
from google_reviews_client.http_client.base_client import BaseHTTPClient


@pytest.fixture()
def mock_credentials():
    """Return a MagicMock simulating google.auth.credentials.Credentials."""
    creds = MagicMock()
    creds.expired = False
    creds.client_id = "724219465644-xxx.apps.googleusercontent.com"
    creds.before_request = MagicMock()
    return creds


@pytest.fixture()
def mock_http_client():
    """Return a MagicMock implementing BaseHTTPClient with .get returning {} by default."""
    client = MagicMock(spec=BaseHTTPClient)
    client.get.return_value = {}
    return client


@pytest.fixture()
def sample_review_data():
    """Return a dict matching the Google API review response format."""
    return {
        "reviewId": "r1",
        "reviewer": {"displayName": "Alice"},
        "starRating": "FIVE",
        "comment": "Great",
        "createTime": "2025-01-15T12:00:00Z",
        "updateTime": "2025-01-15T12:00:00Z",
    }


@pytest.fixture()
def sample_account_data():
    """Return a dict matching the Google API account response format."""
    return {"name": "accounts/123", "accountName": "Test Business"}


@pytest.fixture()
def cli_config(tmp_path):
    """Factory fixture returning a Config object.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        A callable that accepts optional targets and returns a Config.

    """

    def _make(targets=None):
        config_path = tmp_path / "google-reviews-config.123.test@example.com.json"
        return Config(
            path=config_path,
            credentials_data={
                "token": "fake-token",
                "refresh_token": "fake-refresh",
                "client_id": "724219465644-xxx.apps.googleusercontent.com",
                "client_secret": "fake-secret",
                "token_uri": "https://oauth2.googleapis.com/token",
            },
            targets=targets or [],
        )

    return _make
