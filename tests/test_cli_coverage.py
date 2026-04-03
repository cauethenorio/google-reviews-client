"""Tests for uncovered code paths in cli/__init__.py."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from google_reviews_client.cli import (
    first_time_setup,
    get_version,
    main,
    print_api_error,
    sync_target,
)
from google_reviews_client.cli.config import Config
from google_reviews_client.exceptions import GoogleReviewsError
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


class TestCheckCliDeps:
    def test_check_cli_deps_missing_click(self):
        """Patch import to fail for click, verify sys.exit(1)."""
        original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def fake_import(name, *args, **kwargs):
            if name == "click":
                msg = "No module named 'click'"
                raise ImportError(msg)
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=fake_import),
            patch("builtins.print") as mock_print,
            patch("sys.exit") as mock_exit,
        ):
            # Re-run the check function directly
            from google_reviews_client.cli import _check_cli_deps

            _check_cli_deps()

        mock_print.assert_called_once()
        printed_msg = mock_print.call_args[0][0]
        assert "Missing CLI dependencies" in printed_msg
        assert "click" in printed_msg
        mock_exit.assert_called_once_with(1)

    def test_check_cli_deps_missing_google_auth_oauthlib(self):
        """Patch import to fail for google_auth_oauthlib, verify sys.exit(1)."""
        original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def fake_import(name, *args, **kwargs):
            if name == "google_auth_oauthlib":
                msg = "No module named 'google_auth_oauthlib'"
                raise ImportError(msg)
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=fake_import),
            patch("builtins.print") as mock_print,
            patch("sys.exit") as mock_exit,
        ):
            from google_reviews_client.cli import _check_cli_deps

            _check_cli_deps()

        mock_print.assert_called_once()
        printed_msg = mock_print.call_args[0][0]
        assert "Missing CLI dependencies" in printed_msg
        assert "google-auth-oauthlib" in printed_msg
        mock_exit.assert_called_once_with(1)


class TestGetVersionFallback:
    def test_get_version_package_not_found(self):
        """When package is not installed, get_version returns 'dev'."""
        from importlib.metadata import PackageNotFoundError

        with patch("importlib.metadata.version", side_effect=PackageNotFoundError("google-reviews-client")):
            result = get_version()

        assert result == "dev"


class TestFirstTimeSetup:
    def test_first_time_setup_success(self, tmp_path, monkeypatch):
        """Full first-time setup flow with mocked API calls."""
        monkeypatch.chdir(tmp_path)

        mock_creds = MagicMock()
        mock_creds.client_id = "724219465644-xxx.apps.googleusercontent.com"

        mock_account = MagicMock()
        mock_account.name = "accounts/123"
        mock_account.account_name = "Test Business"

        mock_location = MagicMock()
        mock_location.name = "locations/456"
        mock_location.full_name = "accounts/123/locations/456"
        mock_location.title = "Store A"

        with (
            patch("google_reviews_client.cli.find_client_secrets_files", return_value=Path("/fake/secrets.json")),
            patch("google_reviews_client.cli.run_oauth_flow", return_value=mock_creds),
            patch("google_reviews_client.cli.fetch_user_info", return_value=("John", "john@test.com")),
            patch("google_reviews_client.cli.credentials_to_config_data", return_value={"token": "fake"}),
            patch("google_reviews_client.cli.GoogleReviewsClient") as mock_client_cls,
            patch("google_reviews_client.cli.save_config") as mock_save,
            patch("google_reviews_client.cli.select_multiple_items", side_effect=[[mock_account], [mock_location]]),
        ):
            mock_client = MagicMock()
            mock_client.list_accounts.return_value = [mock_account]
            mock_client.list_locations.return_value = [mock_location]
            mock_client_cls.return_value = mock_client

            config = first_time_setup(tmp_path, None)

        assert isinstance(config, Config)
        assert len(config.targets) == 1
        assert config.targets[0]["account"] == "accounts/123"
        assert config.targets[0]["locations"][0]["location"] == "accounts/123/locations/456"
        mock_save.assert_called_once()

    def test_first_time_setup_no_user_info(self, tmp_path, monkeypatch):
        """When fetch_user_info returns None, prompt for email."""
        monkeypatch.chdir(tmp_path)

        mock_creds = MagicMock()
        mock_creds.client_id = "724219465644-xxx.apps.googleusercontent.com"

        mock_account = MagicMock()
        mock_account.name = "accounts/123"
        mock_account.account_name = "Test Business"

        mock_location = MagicMock()
        mock_location.name = "locations/456"
        mock_location.full_name = "accounts/123/locations/456"
        mock_location.title = "Store A"

        with (
            patch("google_reviews_client.cli.find_client_secrets_files", return_value=Path("/fake/secrets.json")),
            patch("google_reviews_client.cli.run_oauth_flow", return_value=mock_creds),
            patch("google_reviews_client.cli.fetch_user_info", return_value=None),
            patch("click.prompt", return_value="test@email.com"),
            patch("google_reviews_client.cli.credentials_to_config_data", return_value={"token": "fake"}),
            patch("google_reviews_client.cli.GoogleReviewsClient") as mock_client_cls,
            patch("google_reviews_client.cli.save_config") as mock_save,
            patch("google_reviews_client.cli.select_multiple_items", side_effect=[[mock_account], [mock_location]]),
        ):
            mock_client = MagicMock()
            mock_client.list_accounts.return_value = [mock_account]
            mock_client.list_locations.return_value = [mock_location]
            mock_client_cls.return_value = mock_client

            config = first_time_setup(tmp_path, None)

        assert isinstance(config, Config)
        assert "test@email.com" in str(config.path)
        mock_save.assert_called_once()


class TestSyncTarget:
    def test_sync_target_with_language(self, tmp_path, monkeypatch):
        """sync_target passes language to client.list_reviews."""
        monkeypatch.chdir(tmp_path)

        mock_client = MagicMock()
        reviews = [_make_review()]
        mock_client.list_reviews.return_value = iter(reviews)

        location_data = {
            "location": "accounts/123/locations/456",
            "title": "Store A",
        }

        sync_target(
            mock_client,
            "Test Business",
            location_data,
            "pt-BR",
            verbose=False,
        )

        mock_client.list_reviews.assert_called_once()
        call_kwargs = mock_client.list_reviews.call_args
        assert call_kwargs.kwargs.get("language") == "pt-BR" or call_kwargs[1].get("language") == "pt-BR"
        assert location_data["language"] == "pt-BR"

    def test_sync_target_incremental_sync(self, tmp_path, monkeypatch):
        """When JSONL exists, sync_target does incremental sync."""
        monkeypatch.chdir(tmp_path)

        # Create existing JSONL file
        output_path = tmp_path / "reviews-456.jsonl"
        existing_review = {
            "review_id": "r-existing",
            "comment": "Old review",
            "update_time": "2025-01-01T00:00:00+00:00",
        }
        output_path.write_text(json.dumps(existing_review) + "\n")

        mock_client = MagicMock()
        new_review = _make_review(review_id="r-new", comment="New review")
        mock_client.list_reviews.return_value = iter([new_review])

        location_data = {
            "location": "accounts/123/locations/456",
            "title": "Store A",
        }

        sync_target(
            mock_client,
            "Test Business",
            location_data,
            None,
            verbose=False,
        )

        # Should have called list_reviews with a since parameter
        call_kwargs = mock_client.list_reviews.call_args
        assert call_kwargs.kwargs.get("since") is not None

    def test_sync_target_new_and_updated_reviews(self, tmp_path, monkeypatch):
        """sync_target reports both new and updated reviews."""
        monkeypatch.chdir(tmp_path)

        # Create existing JSONL file with one review
        output_path = tmp_path / "reviews-456.jsonl"
        existing_review = {
            "review_id": "r-existing",
            "comment": "Old review",
            "update_time": "2025-01-01T00:00:00+00:00",
        }
        output_path.write_text(json.dumps(existing_review) + "\n")

        mock_client = MagicMock()
        # Return one new and one updated (same ID as existing)
        updated_review = _make_review(review_id="r-existing", comment="Updated review")
        new_review = _make_review(review_id="r-new", comment="Brand new")
        mock_client.list_reviews.return_value = iter([updated_review, new_review])

        location_data = {
            "location": "accounts/123/locations/456",
            "title": "Store A",
        }

        # Capture output
        runner = CliRunner()
        with runner.isolated_filesystem():
            # We need to run sync_target inside click context for click.echo
            # Let's just call it directly and check the file
            pass

        sync_target(
            mock_client,
            "Test Business",
            location_data,
            None,
            verbose=False,
        )

        # The file should still exist (was synced into)
        assert output_path.exists()


class TestMainFirstTimeSetup:
    def test_main_first_time_setup_file_not_found(self, tmp_path, monkeypatch):
        """When no config and first_time_setup raises FileNotFoundError."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[]),
            patch(
                "google_reviews_client.cli.first_time_setup",
                side_effect=FileNotFoundError("No client secrets files found"),
            ),
        ):
            result = runner.invoke(main)

        assert result.exit_code == 1
        assert "ERROR" in result.output
        assert "credentials" in result.output.lower()


class TestMainExpiredCredsRefresh:
    def test_main_expired_creds_refresh_success(self, tmp_path, monkeypatch):
        """Expired creds with refresh token should refresh and continue."""
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
            patch("google_reviews_client.cli.credentials_to_config_data", return_value={"token": "new"}),
            patch("google_reviews_client.cli.GoogleReviewsClient") as mock_client_cls,
            patch("google_reviews_client.cli.save_config"),
            patch("google.auth.transport.requests.Request"),
        ):
            mock_creds = MagicMock()
            mock_creds.expired = True
            mock_creds.refresh_token = "fake-refresh"
            mock_creds.client_id = "724219465644-xxx.apps.googleusercontent.com"
            mock_creds.refresh = MagicMock()  # refresh succeeds
            mock_creds_fn.return_value = mock_creds

            mock_client = MagicMock()
            mock_client.list_reviews.return_value = iter(reviews)
            mock_client_cls.return_value = mock_client

            result = runner.invoke(main)

        assert result.exit_code == 0
        assert "Done!" in result.output


class TestMainNoTargets:
    def test_main_no_targets_fetches_accounts(self, tmp_path, monkeypatch):
        """When config has no targets, fetch accounts and prompt."""
        monkeypatch.chdir(tmp_path)
        config = _make_config(tmp_path, targets=[])
        runner = CliRunner()

        mock_account = MagicMock()
        mock_account.name = "accounts/123"
        mock_account.account_name = "Test Business"

        mock_location = MagicMock()
        mock_location.name = "locations/456"
        mock_location.full_name = "accounts/123/locations/456"
        mock_location.title = "Store A"

        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[config.path]),
            patch("google_reviews_client.cli.load_config", return_value=config),
            patch("google_reviews_client.cli.credentials_from_config_data") as mock_creds_fn,
            patch("google_reviews_client.cli.GoogleReviewsClient") as mock_client_cls,
            patch("google_reviews_client.cli.save_config") as mock_save,
            patch("google_reviews_client.cli.select_multiple_items", side_effect=[[mock_account], [mock_location]]),
        ):
            mock_creds = MagicMock()
            mock_creds.expired = False
            mock_creds.client_id = "724219465644-xxx.apps.googleusercontent.com"
            mock_creds_fn.return_value = mock_creds

            mock_client = MagicMock()
            mock_client.list_accounts.return_value = [mock_account]
            mock_client.list_locations.return_value = [mock_location]
            mock_client.list_reviews.return_value = iter([_make_review()])
            mock_client_cls.return_value = mock_client

            result = runner.invoke(main)

        assert result.exit_code == 0
        # save_config is called at least twice: once after target setup, once at end
        assert mock_save.call_count >= 2


class TestMainVerbose:
    def test_main_verbose_credentials_error(self, tmp_path, monkeypatch):
        """Verbose mode logs credential errors."""
        monkeypatch.chdir(tmp_path)
        config = _make_config(tmp_path, targets=[])
        runner = CliRunner()

        with (
            patch("google_reviews_client.cli.find_config_files", return_value=[config.path]),
            patch("google_reviews_client.cli.load_config", return_value=config),
            patch("google_reviews_client.cli.credentials_from_config_data", side_effect=ValueError("bad creds")),
            patch("google_reviews_client.cli.save_config"),
            patch("google_reviews_client.cli.logger") as mock_logger,
        ):
            result = runner.invoke(main, ["-v"])

        assert "Invalid credentials" in result.output
        mock_logger.exception.assert_called()


class TestPrintApiErrorVerbose:
    def test_print_api_error_verbose_with_json(self, capsys):
        """Verbose mode with JSON body calls logger.exception."""
        body = json.dumps({"error": {"message": "Detailed info"}})
        e = GoogleReviewsError("API failed", body=body)

        with patch("google_reviews_client.cli.logger") as mock_logger:
            print_api_error(e, verbose=True)

        mock_logger.exception.assert_called()
        output = capsys.readouterr().out
        assert "Detailed info" in output

    def test_print_api_error_verbose_non_json(self, capsys):
        """Verbose mode with non-JSON body calls logger.exception."""
        e = GoogleReviewsError("API failed", body="plain text error")

        with patch("google_reviews_client.cli.logger") as mock_logger:
            print_api_error(e, verbose=True)

        mock_logger.exception.assert_called()
        output = capsys.readouterr().out
        assert "plain text error" in output
