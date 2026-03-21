"""Tests for CLI auth functions (OAuth flow, user info)."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from google_reviews_client.cli.auth import (
    NotInstalledAppError,
    fetch_user_info,
    run_oauth_flow,
)


class TestRunOauthFlow:
    def test_raises_for_web_credentials(self, tmp_path):
        secrets_file = tmp_path / "client_secret.json"
        secrets_file.write_text(json.dumps({"web": {"client_id": "x", "client_secret": "y"}}))
        with pytest.raises(NotInstalledAppError):
            run_oauth_flow(secrets_file)

    def test_runs_flow_for_installed_app(self, tmp_path):
        secrets_file = tmp_path / "client_secret.json"
        secrets_file.write_text(
            json.dumps({
                "installed": {
                    "client_id": "x.apps.googleusercontent.com",
                    "client_secret": "y",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            })
        )
        mock_creds = MagicMock()
        with patch("google_reviews_client.cli.auth.InstalledAppFlow") as mock_flow_cls:
            mock_flow = MagicMock()
            mock_flow.run_local_server.return_value = mock_creds
            mock_flow_cls.from_client_secrets_file.return_value = mock_flow

            result = run_oauth_flow(secrets_file)

        assert result is mock_creds
        mock_flow.run_local_server.assert_called_once_with(port=0)


class TestFetchUserInfo:
    def test_returns_name_and_email(self):
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        response_data = {"name": "Alice", "email": "alice@example.com"}

        with patch("google_reviews_client.cli.auth.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.is_success = True
            mock_resp.json.return_value = response_data
            mock_get.return_value = mock_resp

            result = fetch_user_info(mock_creds)

        assert result == ("Alice", "alice@example.com")

    def test_returns_none_on_failure(self):
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"

        with patch("google_reviews_client.cli.auth.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.is_success = False
            mock_resp.status_code = 401
            mock_get.return_value = mock_resp

            result = fetch_user_info(mock_creds)

        assert result is None

    def test_returns_none_on_http_error(self):
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"

        with patch("google_reviews_client.cli.auth.httpx.get", side_effect=httpx.HTTPError("connection error")):
            result = fetch_user_info(mock_creds)

        assert result is None
