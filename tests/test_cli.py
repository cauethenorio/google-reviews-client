"""Tests for the CLI entry point (click command)."""

from unittest.mock import patch

from click.testing import CliRunner

from google_reviews_client.cli import main
from google_reviews_client.cli.auth import MultipleFilesFoundError, NoFilesFoundError


class TestMainBanner:
    def test_banner_shows_version_and_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        with patch("google_reviews_client.cli._resolve_credentials", side_effect=NoFilesFoundError):
            result = runner.invoke(main)
        assert "google-reviews-client" in result.output
        assert str(tmp_path) in result.output


class TestMainNoCredentials:
    def test_no_files_shows_setup_guide(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        with patch("google_reviews_client.cli._resolve_credentials", side_effect=NoFilesFoundError):
            result = runner.invoke(main)
        assert result.exit_code == 1
        assert "console.cloud.google.com" in result.output


class TestMainMultipleFiles:
    def test_multiple_files_lists_them(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        files = [tmp_path / "credentials.a.json", tmp_path / "credentials.b.json"]
        runner = CliRunner()
        with patch("google_reviews_client.cli._resolve_credentials", side_effect=MultipleFilesFoundError(files)):
            result = runner.invoke(main)
        assert result.exit_code == 1
        assert "credentials.a.json" in result.output
        assert "credentials.b.json" in result.output
