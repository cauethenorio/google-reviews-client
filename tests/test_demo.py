"""Tests for CLI demo helpers."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from google_reviews_client.demo import (
    _build_parser,
    _find_credentials_file,
    _parse_oauth_config,
    _run_oauth_flow,
)


def _write_credentials(path: Path, credential_type: str, redirect_uris: list[str]) -> Path:
    """Helper to write a credentials JSON file."""
    data = {
        credential_type: {
            "client_id": "test.apps.googleusercontent.com",
            "client_secret": "test-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": redirect_uris,
        }
    }
    path.write_text(json.dumps(data))
    return path


class TestFindCredentialsFile:
    """Tests for _find_credentials_file()."""

    def test_single_credentials_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        creds = tmp_path / "credentials.json"
        creds.write_text("{}")

        result = _find_credentials_file()
        assert result == creds

    def test_single_client_secret_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        creds = tmp_path / "client_secret_12345.json"
        creds.write_text("{}")

        result = _find_credentials_file()
        assert result == creds

    def test_single_prefixed_client_secret(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        creds = tmp_path / "myapp_client_secret_12345.json"
        creds.write_text("{}")

        result = _find_credentials_file()
        assert result == creds

    def test_no_files_exits_with_error(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _find_credentials_file()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No credentials file found" in captured.out
        assert "credentials.json" in captured.out

    def test_multiple_files_exits_with_error(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "credentials.json").write_text("{}")
        (tmp_path / "client_secret_abc.json").write_text("{}")

        with pytest.raises(SystemExit) as exc_info:
            _find_credentials_file()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Multiple credential files found" in captured.out

    def test_deduplication_single_match(self, tmp_path, monkeypatch):
        """A file matching multiple patterns is counted only once."""
        monkeypatch.chdir(tmp_path)
        # credentials.json matches the first pattern only
        creds = tmp_path / "credentials.json"
        creds.write_text("{}")

        result = _find_credentials_file()
        assert result == creds


class TestParseOauthConfig:
    """Tests for _parse_oauth_config()."""

    def test_installed_localhost_no_port_infers_80(self, tmp_path):
        creds = _write_credentials(tmp_path / "creds.json", "installed", ["http://localhost"])

        assert _parse_oauth_config(creds) == 80

    def test_installed_localhost_with_port(self, tmp_path):
        creds = _write_credentials(tmp_path / "creds.json", "installed", ["http://localhost:9090"])

        assert _parse_oauth_config(creds) == 9090

    def test_installed_127_0_0_1_with_port(self, tmp_path):
        creds = _write_credentials(tmp_path / "creds.json", "installed", ["http://127.0.0.1:8080"])

        assert _parse_oauth_config(creds) == 8080

    def test_installed_ipv6_localhost_with_port(self, tmp_path):
        creds = _write_credentials(tmp_path / "creds.json", "installed", ["http://[::1]:7070"])

        assert _parse_oauth_config(creds) == 7070

    def test_web_localhost_with_port(self, tmp_path):
        creds = _write_credentials(tmp_path / "creds.json", "web", ["http://localhost:8080"])

        assert _parse_oauth_config(creds) == 8080

    def test_oob_uri_exits_with_error(self, tmp_path, capsys):
        creds = _write_credentials(tmp_path / "creds.json", "installed", ["urn:ietf:wg:oauth:2.0:oob"])

        with pytest.raises(SystemExit) as exc_info:
            _parse_oauth_config(creds)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "OOB" in captured.out
        assert "no longer supported" in captured.out

    def test_web_non_localhost_exits_with_error(self, tmp_path, capsys):
        creds = _write_credentials(tmp_path / "creds.json", "web", ["https://myapp.com/callback"])

        with pytest.raises(SystemExit) as exc_info:
            _parse_oauth_config(creds)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "localhost redirect URI" in captured.out

    def test_oob_with_localhost_uses_localhost(self, tmp_path):
        creds = _write_credentials(
            tmp_path / "creds.json",
            "installed",
            ["urn:ietf:wg:oauth:2.0:oob", "http://localhost:8080"],
        )

        assert _parse_oauth_config(creds) == 8080

    def test_multiple_uris_first_localhost_wins(self, tmp_path):
        creds = _write_credentials(
            tmp_path / "creds.json",
            "installed",
            ["https://example.com/callback", "http://localhost:3000", "http://localhost:4000"],
        )

        assert _parse_oauth_config(creds) == 3000

    def test_invalid_json_raises_error(self, tmp_path):
        creds = tmp_path / "creds.json"
        creds.write_text("not json")

        with pytest.raises(json.JSONDecodeError):
            _parse_oauth_config(creds)

    def test_missing_installed_and_web_key_exits(self, tmp_path, capsys):
        creds = tmp_path / "creds.json"
        creds.write_text(json.dumps({"other": {}}))

        with pytest.raises(SystemExit) as exc_info:
            _parse_oauth_config(creds)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "missing 'installed' or 'web' key" in captured.out

    def test_installed_no_redirect_uris_exits(self, tmp_path, capsys):
        creds = tmp_path / "creds.json"
        creds.write_text(json.dumps({"installed": {"client_id": "test"}}))

        with pytest.raises(SystemExit) as exc_info:
            _parse_oauth_config(creds)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No supported redirect URI" in captured.out


class TestRunOauthFlow:
    """Tests for _run_oauth_flow()."""

    def test_calls_run_local_server_with_port(self, tmp_path):
        mock_flow = MagicMock()
        mock_installed_app_flow = MagicMock()
        mock_installed_app_flow.from_client_secrets_file.return_value = mock_flow

        mock_module = MagicMock()
        mock_module.InstalledAppFlow = mock_installed_app_flow

        creds_path = tmp_path / "creds.json"
        with patch.dict("sys.modules", {"google_auth_oauthlib": MagicMock(), "google_auth_oauthlib.flow": mock_module}):
            _run_oauth_flow(creds_path, 9090)

        mock_installed_app_flow.from_client_secrets_file.assert_called_once_with(
            str(creds_path), scopes=["https://www.googleapis.com/auth/business.manage"]
        )
        mock_flow.run_local_server.assert_called_once_with(port=9090)


class TestBuildParser:
    """Tests for argparse parser in isolation."""

    def test_no_flags_defaults(self):
        parser = _build_parser()
        args = parser.parse_args([])

        assert args.credentials is None
        assert args.output == Path("reviews.json")

    def test_credentials_flag_short(self):
        parser = _build_parser()
        args = parser.parse_args(["-c", "path/to/creds.json"])

        assert args.credentials == Path("path/to/creds.json")

    def test_credentials_flag_long(self):
        parser = _build_parser()
        args = parser.parse_args(["--credentials", "path/to/creds.json"])

        assert args.credentials == Path("path/to/creds.json")

    def test_output_flag_short(self):
        parser = _build_parser()
        args = parser.parse_args(["-o", "custom.json"])

        assert args.output == Path("custom.json")

    def test_output_flag_long(self):
        parser = _build_parser()
        args = parser.parse_args(["--output", "custom.json"])

        assert args.output == Path("custom.json")

    def test_both_flags(self):
        parser = _build_parser()
        args = parser.parse_args(["-c", "creds.json", "-o", "out.json"])

        assert args.credentials == Path("creds.json")
        assert args.output == Path("out.json")
