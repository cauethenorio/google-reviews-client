"""Tests for the CLI entry point (click command)."""

from unittest.mock import patch

from click.testing import CliRunner

from google_reviews_client.cli import main, select_multiple_items


class TestMainBanner:
    def test_banner_shows_version_and_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[]),
            patch("google_reviews_client.cli.first_time_setup", side_effect=FileNotFoundError("No files")),
        ):
            result = runner.invoke(main)
        assert "google-reviews-client" in result.output
        assert str(tmp_path) in result.output


class TestMainNoCredentials:
    def test_no_files_shows_setup_guide(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[]),
            patch("google_reviews_client.cli.first_time_setup", side_effect=FileNotFoundError("No files")),
        ):
            result = runner.invoke(main)
        assert result.exit_code == 1
        assert "console.cloud.google.com" in result.output


class TestSelectMultipleItems:
    def test_auto_selects_single_item(self):
        items = [{"name": "only"}]
        result = select_multiple_items(items, "thing", "{0[name]}")
        assert result == items

    def test_returns_empty_for_empty_list(self):
        result = select_multiple_items([], "thing", "{0}")
        assert result == []
