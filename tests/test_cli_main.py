"""Tests for the CLI main command and error handling."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from google_reviews_client.cli import (
    main,
    print_api_error,
    print_quota_error,
    select_multiple_items,
)
from google_reviews_client.cli.auth import MultipleFilesFoundError, NotInstalledAppError
from google_reviews_client.cli.config import Config
from google_reviews_client.exceptions import (
    AuthenticationError,
    GoogleReviewsError,
    RateLimitError,
)
from google_reviews_client.models import Review, Reviewer, StarRating


def _make_review(review_id="r1", comment="Great", rating=StarRating.FIVE):
    return Review(
        review_id=review_id,
        reviewer=Reviewer(display_name="Alice"),
        star_rating=rating,
        comment=comment,
        create_time=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
        update_time=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
    )


def _make_config(tmp_path, targets=None):
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


class TestMainMultipleSecretsFiles:
    def test_shows_error_with_file_list(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        files = [tmp_path / "client_secret_a.json", tmp_path / "client_secret_b.json"]
        runner = CliRunner()
        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[]),
            patch("google_reviews_client.cli.first_time_setup", side_effect=MultipleFilesFoundError(files)),
        ):
            result = runner.invoke(main)
        assert result.exit_code == 1
        assert "Multiple client secrets files found" in result.output
        assert "client_secret_a.json" in result.output


class TestMainNotInstalledApp:
    def test_shows_desktop_app_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[]),
            patch("google_reviews_client.cli.first_time_setup", side_effect=NotInstalledAppError()),
        ):
            result = runner.invoke(main)
        assert result.exit_code == 1
        assert "Desktop app" in result.output or "installed" in result.output


class TestMainWithConfig:
    def test_syncs_reviews(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = _make_config(
            tmp_path,
            targets=[
                {
                    "account": "accounts/123",
                    "account_name": "My Business",
                    "locations": [{"location": "accounts/123/locations/456", "title": "Store A"}],
                }
            ],
        )
        runner = CliRunner()
        reviews = [_make_review()]
        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[config.path]),
            patch("google_reviews_client.cli.load_config", return_value=config),
            patch("google_reviews_client.cli.credentials_from_config_data") as mock_creds_fn,
            patch("google_reviews_client.cli.GoogleReviewsClient") as mock_client_cls,
            patch("google_reviews_client.cli.save_config"),
        ):
            mock_creds = MagicMock()
            mock_creds.expired = False
            mock_creds.client_id = "724219465644-xxx.apps.googleusercontent.com"
            mock_creds_fn.return_value = mock_creds
            mock_client = MagicMock()
            mock_client.list_reviews.return_value = iter(reviews)
            mock_client_cls.return_value = mock_client

            result = runner.invoke(main)

        assert result.exit_code == 0
        assert "Done!" in result.output
        output_path = tmp_path / "reviews-456.jsonl"
        assert output_path.exists()

    def test_handles_rate_limit_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = _make_config(
            tmp_path,
            targets=[
                {
                    "account": "accounts/123",
                    "account_name": "My Business",
                    "locations": [{"location": "accounts/123/locations/456", "title": "Store A"}],
                }
            ],
        )
        runner = CliRunner()
        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[config.path]),
            patch("google_reviews_client.cli.load_config", return_value=config),
            patch("google_reviews_client.cli.credentials_from_config_data") as mock_creds_fn,
            patch("google_reviews_client.cli.GoogleReviewsClient") as mock_client_cls,
            patch("google_reviews_client.cli.save_config"),
        ):
            mock_creds = MagicMock()
            mock_creds.expired = False
            mock_creds.client_id = "724219465644-xxx.apps.googleusercontent.com"
            mock_creds_fn.return_value = mock_creds
            mock_client = MagicMock()
            mock_client.list_reviews.side_effect = RateLimitError("Rate limit", body="")
            mock_client_cls.return_value = mock_client

            result = runner.invoke(main)

        assert "quota exceeded" in result.output.lower() or "API quota" in result.output

    def test_handles_auth_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = _make_config(
            tmp_path,
            targets=[
                {
                    "account": "accounts/123",
                    "account_name": "My Business",
                    "locations": [{"location": "accounts/123/locations/456", "title": "Store A"}],
                }
            ],
        )
        runner = CliRunner()
        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[config.path]),
            patch("google_reviews_client.cli.load_config", return_value=config),
            patch("google_reviews_client.cli.credentials_from_config_data") as mock_creds_fn,
            patch("google_reviews_client.cli.GoogleReviewsClient") as mock_client_cls,
            patch("google_reviews_client.cli.save_config"),
        ):
            mock_creds = MagicMock()
            mock_creds.expired = False
            mock_creds.client_id = None
            mock_creds_fn.return_value = mock_creds
            mock_client = MagicMock()
            mock_client.list_reviews.side_effect = AuthenticationError("Auth failed", body="")
            mock_client_cls.return_value = mock_client

            result = runner.invoke(main)

        assert "Authentication failed" in result.output

    def test_handles_generic_api_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = _make_config(
            tmp_path,
            targets=[
                {
                    "account": "accounts/123",
                    "account_name": "My Business",
                    "locations": [{"location": "accounts/123/locations/456", "title": "Store A"}],
                }
            ],
        )
        runner = CliRunner()
        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[config.path]),
            patch("google_reviews_client.cli.load_config", return_value=config),
            patch("google_reviews_client.cli.credentials_from_config_data") as mock_creds_fn,
            patch("google_reviews_client.cli.GoogleReviewsClient") as mock_client_cls,
            patch("google_reviews_client.cli.save_config"),
        ):
            mock_creds = MagicMock()
            mock_creds.expired = False
            mock_creds.client_id = None
            mock_creds_fn.return_value = mock_creds
            mock_client = MagicMock()
            mock_client.list_reviews.side_effect = GoogleReviewsError(
                "Something broke",
                body=json.dumps({"error": {"message": "Detailed error info"}}),
            )
            mock_client_cls.return_value = mock_client

            result = runner.invoke(main)

        assert "Something broke" in result.output

    def test_invalid_credentials_continues(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = _make_config(tmp_path, targets=[])
        runner = CliRunner()
        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[config.path]),
            patch("google_reviews_client.cli.load_config", return_value=config),
            patch("google_reviews_client.cli.credentials_from_config_data", side_effect=ValueError("bad creds")),
            patch("google_reviews_client.cli.save_config"),
        ):
            result = runner.invoke(main)

        assert "Invalid credentials" in result.output

    def test_expired_credentials_refresh_failure(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = _make_config(tmp_path, targets=[])
        runner = CliRunner()
        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[config.path]),
            patch("google_reviews_client.cli.load_config", return_value=config),
            patch("google_reviews_client.cli.credentials_from_config_data") as mock_creds_fn,
            patch("google_reviews_client.cli.save_config"),
        ):
            mock_creds = MagicMock()
            mock_creds.expired = True
            mock_creds.refresh_token = "fake-refresh"
            mock_creds.refresh.side_effect = Exception("refresh failed")
            mock_creds_fn.return_value = mock_creds

            result = runner.invoke(main)

        assert "Failed to refresh" in result.output

    def test_no_new_reviews(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = _make_config(
            tmp_path,
            targets=[
                {
                    "account": "accounts/123",
                    "account_name": "My Business",
                    "locations": [{"location": "accounts/123/locations/456", "title": "Store A"}],
                }
            ],
        )
        runner = CliRunner()
        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[config.path]),
            patch("google_reviews_client.cli.load_config", return_value=config),
            patch("google_reviews_client.cli.credentials_from_config_data") as mock_creds_fn,
            patch("google_reviews_client.cli.GoogleReviewsClient") as mock_client_cls,
            patch("google_reviews_client.cli.save_config"),
        ):
            mock_creds = MagicMock()
            mock_creds.expired = False
            mock_creds.client_id = None
            mock_creds_fn.return_value = mock_creds
            mock_client = MagicMock()
            mock_client.list_reviews.return_value = iter([])
            mock_client_cls.return_value = mock_client

            result = runner.invoke(main)

        assert "no new reviews" in result.output


class TestSelectMultipleItemsInteractive:
    def test_select_all(self):
        items = [{"name": "a"}, {"name": "b"}]
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                _make_select_command(items, "item", "{0[name]}"),
                input="a\n",
            )
        assert result.exit_code == 0

    def test_select_specific(self):
        items = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                _make_select_command(items, "item", "{0[name]}"),
                input="1,3\n",
            )
        assert result.exit_code == 0

    def test_invalid_then_valid(self):
        items = [{"name": "a"}, {"name": "b"}]
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                _make_select_command(items, "item", "{0[name]}"),
                input="xyz\n1\n",
            )
        assert result.exit_code == 0
        assert "Invalid choice" in result.output


def _make_select_command(items, label, fmt):
    """Create a click command that wraps select_multiple_items for testing."""
    import click

    @click.command()
    def cmd():
        result = select_multiple_items(items, label, fmt)
        click.echo(f"Selected: {len(result)}")

    return cmd


class TestPrintQuotaError:
    def test_prints_quota_info(self, capsys):
        e = RateLimitError("Rate limit", body="")
        print_quota_error(e, verbose=False)
        output = capsys.readouterr().out
        assert "API quota exceeded" in output
        assert "request access" in output.lower() or "access request" in output.lower()

    def test_with_project_number(self, capsys):
        e = RateLimitError("Rate limit", body="")
        print_quota_error(e, verbose=False, project_number="724219465644")
        output = capsys.readouterr().out
        assert "724219465644" in output


class TestPrintApiError:
    def test_prints_error_message(self, capsys):
        e = GoogleReviewsError("Something went wrong", body="")
        print_api_error(e, verbose=False)
        output = capsys.readouterr().out
        assert "Something went wrong" in output

    def test_prints_json_body_message(self, capsys):
        body = json.dumps({"error": {"message": "Detailed info"}})
        e = GoogleReviewsError("API failed", body=body)
        print_api_error(e, verbose=False)
        output = capsys.readouterr().out
        assert "Detailed info" in output

    def test_prints_non_json_body(self, capsys):
        e = GoogleReviewsError("API failed", body="plain text error")
        print_api_error(e, verbose=False)
        output = capsys.readouterr().out
        assert "plain text error" in output
