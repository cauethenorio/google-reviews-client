"""Tests for CLI demo helpers."""

import errno
import json
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from google_reviews_client.demo import (
    _build_parser,
    _find_credentials_file,
    _get_version,
    _parse_oauth_config,
    _print_banner,
    _run_oauth_flow,
    _validate_ports,
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

        assert _parse_oauth_config(creds) == ("installed", [80], ["http://localhost"])

    def test_installed_localhost_with_port(self, tmp_path):
        creds = _write_credentials(tmp_path / "creds.json", "installed", ["http://localhost:9090"])

        assert _parse_oauth_config(creds) == ("installed", [9090], ["http://localhost:9090"])

    def test_installed_127_0_0_1_with_port(self, tmp_path):
        creds = _write_credentials(tmp_path / "creds.json", "installed", ["http://127.0.0.1:8080"])

        assert _parse_oauth_config(creds) == ("installed", [8080], ["http://127.0.0.1:8080"])

    def test_installed_ipv6_localhost_with_port(self, tmp_path):
        creds = _write_credentials(tmp_path / "creds.json", "installed", ["http://[::1]:7070"])

        assert _parse_oauth_config(creds) == ("installed", [7070], ["http://[::1]:7070"])

    def test_web_localhost_with_port(self, tmp_path):
        creds = _write_credentials(tmp_path / "creds.json", "web", ["http://localhost:8080"])

        assert _parse_oauth_config(creds) == ("web", [8080], ["http://localhost:8080"])

    def test_oob_uri_returns_empty_ports(self, tmp_path):
        creds = _write_credentials(tmp_path / "creds.json", "installed", ["urn:ietf:wg:oauth:2.0:oob"])

        assert _parse_oauth_config(creds) == ("installed", [], ["urn:ietf:wg:oauth:2.0:oob"])

    def test_web_non_localhost_returns_empty_ports(self, tmp_path):
        creds = _write_credentials(tmp_path / "creds.json", "web", ["https://myapp.com/callback"])

        assert _parse_oauth_config(creds) == ("web", [], ["https://myapp.com/callback"])

    def test_oob_with_localhost_uses_localhost(self, tmp_path):
        uris = ["urn:ietf:wg:oauth:2.0:oob", "http://localhost:8080"]
        creds = _write_credentials(tmp_path / "creds.json", "installed", uris)

        assert _parse_oauth_config(creds) == ("installed", [8080], uris)

    def test_multiple_localhost_uris_returns_all_ports(self, tmp_path):
        uris = ["https://example.com/callback", "http://localhost:3000", "http://localhost:4000"]
        creds = _write_credentials(tmp_path / "creds.json", "installed", uris)

        assert _parse_oauth_config(creds) == ("installed", [3000, 4000], uris)

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

    def test_installed_no_redirect_uris_returns_empty(self, tmp_path):
        creds = tmp_path / "creds.json"
        creds.write_text(json.dumps({"installed": {"client_id": "test"}}))

        assert _parse_oauth_config(creds) == ("installed", [], [])


class TestValidatePorts:
    """Tests for _validate_ports()."""

    def test_ports_present_does_not_exit(self):
        _validate_ports([8080], [], "installed")  # should not raise

    def test_oob_uri_exits_with_error(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            _validate_ports([], ["urn:ietf:wg:oauth:2.0:oob"], "installed")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "OOB" in captured.out
        assert "no longer supported" in captured.out

    def test_web_non_localhost_exits_with_error(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            _validate_ports([], ["https://myapp.com/callback"], "web")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "localhost redirect URI" in captured.out

    def test_no_redirect_uris_exits_with_error(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            _validate_ports([], [], "installed")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No supported redirect URI" in captured.out


class TestRunOauthFlow:
    """Tests for _run_oauth_flow()."""

    def test_calls_run_local_server_with_first_port(self, tmp_path):
        mock_flow = MagicMock()
        mock_installed_app_flow = MagicMock()
        mock_installed_app_flow.from_client_secrets_file.return_value = mock_flow

        mock_module = MagicMock()
        mock_module.InstalledAppFlow = mock_installed_app_flow

        creds_path = tmp_path / "creds.json"
        with patch.dict("sys.modules", {"google_auth_oauthlib": MagicMock(), "google_auth_oauthlib.flow": mock_module}):
            _run_oauth_flow(creds_path, [9090], [], "installed")

        mock_installed_app_flow.from_client_secrets_file.assert_called_once_with(
            str(creds_path), scopes=["https://www.googleapis.com/auth/business.manage"]
        )
        mock_flow.run_local_server.assert_called_once_with(port=9090)


class TestRunOauthFlowRetry:
    """Tests for port retry logic in _run_oauth_flow()."""

    def test_first_port_fails_second_succeeds(self, tmp_path, capsys):
        mock_creds = MagicMock()
        mock_flow = MagicMock()
        mock_flow.run_local_server.side_effect = [OSError(errno.EADDRINUSE, "Address already in use"), mock_creds]
        mock_installed_app_flow = MagicMock()
        mock_installed_app_flow.from_client_secrets_file.return_value = mock_flow

        mock_module = MagicMock()
        mock_module.InstalledAppFlow = mock_installed_app_flow

        creds_path = tmp_path / "creds.json"
        with patch.dict("sys.modules", {"google_auth_oauthlib": MagicMock(), "google_auth_oauthlib.flow": mock_module}):
            result = _run_oauth_flow(creds_path, [8080, 9090], [], "installed")

        assert result == mock_creds
        captured = capsys.readouterr()
        assert "Port 8080 is in use" in captured.out
        assert "trying 9090" in captured.out

    def test_all_ports_fail_exits(self, tmp_path, capsys):
        mock_flow = MagicMock()
        mock_flow.run_local_server.side_effect = OSError(errno.EADDRINUSE, "Address already in use")
        mock_installed_app_flow = MagicMock()
        mock_installed_app_flow.from_client_secrets_file.return_value = mock_flow

        mock_module = MagicMock()
        mock_module.InstalledAppFlow = mock_installed_app_flow

        creds_path = tmp_path / "creds.json"
        with (
            patch.dict("sys.modules", {"google_auth_oauthlib": MagicMock(), "google_auth_oauthlib.flow": mock_module}),
            pytest.raises(SystemExit) as exc_info,
        ):
            _run_oauth_flow(creds_path, [8080, 9090], [], "installed")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Could not start OAuth callback server" in captured.out
        assert "All configured ports are in use: 8080, 9090" in captured.out

    def test_single_port_fails_exits(self, tmp_path, capsys):
        mock_flow = MagicMock()
        mock_flow.run_local_server.side_effect = OSError(errno.EADDRINUSE, "Address already in use")
        mock_installed_app_flow = MagicMock()
        mock_installed_app_flow.from_client_secrets_file.return_value = mock_flow

        mock_module = MagicMock()
        mock_module.InstalledAppFlow = mock_installed_app_flow

        creds_path = tmp_path / "creds.json"
        with (
            patch.dict("sys.modules", {"google_auth_oauthlib": MagicMock(), "google_auth_oauthlib.flow": mock_module}),
            pytest.raises(SystemExit) as exc_info,
        ):
            _run_oauth_flow(creds_path, [8080], [], "installed")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Could not start OAuth callback server" in captured.out
        assert "Port 8080 is already in use" in captured.out
        assert "trying" not in captured.out


class TestGetVersion:
    """Tests for _get_version()."""

    def test_returns_installed_version(self):
        with patch("importlib.metadata.version", return_value="1.2.3"):
            assert _get_version() == "1.2.3"

    def test_returns_dev_when_not_installed(self):
        with patch("importlib.metadata.version", side_effect=PackageNotFoundError("not found")):
            assert _get_version() == "dev"


class TestPrintBanner:
    """Tests for _print_banner()."""

    def test_banner_includes_version(self, capsys):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            _print_banner(Path("creds.json"), "auto-detected", "installed", [8080])

        captured = capsys.readouterr()
        assert "google-reviews-client" in captured.out
        assert "v1.0.0" in captured.out

    def test_banner_shows_credentials_path(self, capsys):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            _print_banner(Path("my/creds.json"), "auto-detected", "installed", [8080])

        captured = capsys.readouterr()
        assert "my/creds.json" in captured.out
        assert "auto-detected" in captured.out

    def test_banner_shows_specified_via_flag(self, capsys):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            _print_banner(Path("creds.json"), "specified via -c", "installed", [8080])

        captured = capsys.readouterr()
        assert "specified via -c" in captured.out

    def test_banner_shows_credential_type_desktop(self, capsys):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            _print_banner(Path("creds.json"), "auto-detected", "installed", [8080])

        captured = capsys.readouterr()
        assert "Desktop" in captured.out
        assert "installed" in captured.out

    def test_banner_shows_credential_type_web(self, capsys):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            _print_banner(Path("creds.json"), "auto-detected", "web", [8080])

        captured = capsys.readouterr()
        assert "Web" in captured.out

    def test_banner_shows_port(self, capsys):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            _print_banner(Path("creds.json"), "auto-detected", "installed", [8080])

        captured = capsys.readouterr()
        assert "8080" in captured.out

    def test_banner_shows_fallback_ports(self, capsys):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            _print_banner(Path("creds.json"), "auto-detected", "installed", [8080, 9090])

        captured = capsys.readouterr()
        assert "8080" in captured.out
        assert "fallback: 9090" in captured.out

    def test_banner_no_ports_omits_port_line(self, capsys):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            _print_banner(Path("creds.json"), "auto-detected", "installed", [])

        captured = capsys.readouterr()
        assert "OAuth port" not in captured.out


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
