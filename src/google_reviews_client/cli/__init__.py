"""CLI for Google Reviews Client.

Usage:
    google-reviews                                    # auto-detect credentials
    google-reviews --client-secrets-file /path/to/secrets.json
    google-reviews --tokens-file /path/to/tokens.json
    google-reviews -v                                 # verbose mode
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import click

from google_reviews_client.client import GoogleReviewsClient
from google_reviews_client.exceptions import (
    AuthenticationError,
    GoogleReviewsError,
)
from google_reviews_client.exceptions import (
    PermissionError as APIPermissionError,
)

from .auth import (
    MultipleFilesFoundError,
    NoFilesFoundError,
    NotInstalledAppError,
    find_client_secrets_files,
    find_tokens_files,
    load_tokens,
    run_oauth_flow,
    save_tokens,
)
from .logger import add_verbose_option

logger = logging.getLogger(__name__)
auth_logger = logging.getLogger("google_reviews_client.cli.auth")


def _get_version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("google-reviews-client")
    except PackageNotFoundError:
        return "dev"


def _print_banner() -> None:
    click.echo(click.style(f"google-reviews-client v{_get_version()}", bold=True))
    click.echo(click.style(f"Directory: {Path.cwd()}", dim=True))
    click.echo()


def _select_item(items: list, label: str, format_str: str):
    """Let user select from a list, auto-select if only one."""
    if not items:
        click.echo(click.style(f"No {label}s found.", fg="red"))
        sys.exit(1)

    if len(items) == 1:
        display = format_str.format(items[0])
        click.echo(f"  Using {label}: {display}")
        return items[0]

    click.echo(click.style(f"\nAvailable {label}s:", bold=True))
    for i, item in enumerate(items, 1):
        display = format_str.format(item)
        click.echo(f"  {click.style(f'{i}.', dim=True)} {display}")

    while True:
        choice = click.prompt(f"\nSelect {label}", type=click.IntRange(1, len(items)))
        return items[choice - 1]


def _print_reviews_table(reviews: list) -> None:
    truncate = 60
    header = f"  {'Date':<12}{'Rating':<8}{'Review':<64}{'Reply':<5}"
    click.echo(click.style(header, bold=True))
    click.echo(f"  {'-' * 87}")
    for review in reviews:
        date_str = review.create_time.strftime("%Y-%m-%d")
        comment = review.comment[:truncate] + "..." if len(review.comment) > truncate else review.comment
        reply = "Yes" if review.has_reply else "No"
        click.echo(f"  {date_str:<12}{review.rating_value:<8}{comment:<64}{reply:<5}")
    click.echo()


def _read_max_update_time(path: Path) -> datetime | None:
    max_update_time: datetime | None = None
    with path.open() as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if not stripped:
                continue
            review_dict = json.loads(stripped)
            ut = datetime.fromisoformat(review_dict["update_time"])
            if max_update_time is None or ut > max_update_time:
                max_update_time = ut
    return max_update_time


def _write_reviews_jsonl(reviews: list, path: Path, *, append: bool = False) -> None:
    mode = "a" if append else "w"
    with path.open(mode) as f:
        for review in reviews:
            f.write(json.dumps(review.to_dict(), ensure_ascii=False) + "\n")


def _print_api_error(e: GoogleReviewsError, *, verbose: bool) -> None:
    """Print a clean API error message, extracting details from JSON body if possible."""
    click.echo(click.style("\nERROR: ", fg="red") + str(e))

    if not e.body:
        return

    # Try to extract a clean message from the JSON error body
    try:
        data = json.loads(e.body)
        error_info = data.get("error", {})
        message = error_info.get("message", "")
        if message:
            click.echo(f"  {message}")
        if verbose:
            logger.exception("API error details")
    except (json.JSONDecodeError, AttributeError):
        click.echo(f"  Details: {e.body}")
        if verbose:
            logger.exception("API error details")


def _resolve_credentials(cwd: Path, tokens_file: Path | None, client_secrets_file: Path | None):
    """Resolve credentials: try tokens first, then OAuth flow.

    If --client-secrets-file is explicitly provided, skip tokens search
    and go straight to OAuth flow (the user wants to use that specific project).

    Raises NoFilesFoundError, MultipleFilesFoundError, NotInstalledAppError.
    """
    # If client-secrets-file was explicitly provided, skip tokens and run OAuth
    if client_secrets_file is None:
        try:
            path = find_tokens_files(cwd, explicit_path=tokens_file)
            return load_tokens(path)
        except NoFilesFoundError:
            logger.debug("No tokens files found, will try OAuth flow")
        except MultipleFilesFoundError:
            raise

    # No tokens — run OAuth flow
    path = find_client_secrets_files(cwd, explicit_path=client_secrets_file)
    creds = run_oauth_flow(path)
    save_tokens(cwd, creds)
    return creds


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--client-secrets-file",
    help="Path to OAuth client secrets JSON file (auto-detected if not specified).",
    default=None,
    type=click.Path(exists=True, file_okay=True, readable=True, path_type=Path),
)
@click.option(
    "--tokens-file",
    help="Path to tokens JSON file from previous OAuth flow (auto-detected if not specified).",
    default=None,
    type=click.Path(exists=True, file_okay=True, readable=True, path_type=Path),
)
@add_verbose_option([logger, auth_logger])
def main(client_secrets_file, tokens_file, verbose):
    """Download all your Google Business reviews."""

    _print_banner()
    cwd = Path.cwd()

    # --- Resolve credentials ---
    try:
        creds = _resolve_credentials(cwd, tokens_file, client_secrets_file)
    except NoFilesFoundError:
        click.echo(click.style("ERROR: ", fg="red") + "No credentials or client secrets files found.\n")
        click.echo("To set up credentials:")
        click.echo("1. Go to https://console.cloud.google.com/apis/credentials")
        click.echo("2. Create an OAuth 2.0 Client ID (Desktop application)")
        click.echo("3. Download the JSON file to this directory\n")
        click.echo("Expected file names: client_secret*.json")
        click.echo("\nYou also need to request access to the Google Business Profile API:")
        click.echo("  https://developers.google.com/my-business/content/basic-setup")
        sys.exit(1)
    except MultipleFilesFoundError as e:
        click.echo(click.style("ERROR: ", fg="red") + "Multiple credential files found:")
        for path in e.files_found:
            click.echo(f"  {click.style(str(path.relative_to(cwd)), fg='yellow')}")
        click.echo("\nSpecify which file to use:")
        click.echo("  google-reviews --tokens-file <path>")
        click.echo("  google-reviews --client-secrets-file <path>")
        sys.exit(1)
    except NotInstalledAppError:
        click.echo(click.style("ERROR: ", fg="red") + "Only desktop (installed) app credentials are supported.\n")
        click.echo("Your client secrets file uses 'web' type credentials.")
        click.echo("To fix this:")
        click.echo("1. Go to https://console.cloud.google.com/apis/credentials")
        click.echo("2. Create an OAuth 2.0 Client ID with type 'Desktop app'")
        click.echo("3. Download the new JSON file to this directory")
        sys.exit(1)

    client = GoogleReviewsClient(credentials=creds)

    # --- Fetch accounts and locations ---
    try:
        click.echo(click.style("Fetching accounts...", fg="cyan"))
        accounts = client.list_accounts()
        account = _select_item(accounts, "account", "{0.name} | {0.account_name}")

        click.echo(click.style("Fetching locations...", fg="cyan"))
        locations = client.list_locations(account.name)
        location = _select_item(locations, "location", "{0.name} | {0.title}")
    except AuthenticationError:
        click.echo(click.style("\nERROR: ", fg="red") + "Authentication failed.\n")
        click.echo("Your API access may not be approved. To request access:")
        click.echo("  https://developers.google.com/my-business/content/basic-setup\n")
        click.echo("Make sure the Google Business Profile API is enabled in your project.")
        if verbose:
            logger.exception("Authentication error details")
        sys.exit(1)
    except APIPermissionError as e:
        _print_api_error(e, verbose=verbose)
        sys.exit(1)
    except GoogleReviewsError as e:
        _print_api_error(e, verbose=verbose)
        sys.exit(1)

    # --- Fetch and save reviews ---
    output_path = Path(f"reviews-{location.location_id}.jsonl")
    since = _read_max_update_time(output_path) if output_path.exists() else None

    try:
        if since is not None:
            click.echo(click.style(f"\nSyncing reviews since {since.isoformat()}...", fg="cyan"))
        else:
            click.echo(click.style(f"\nFetching all reviews for {location.title}...", fg="cyan"))

        reviews = list(client.list_reviews(location.full_name, since=since))
    except GoogleReviewsError as e:
        _print_api_error(e, verbose=verbose)
        sys.exit(1)

    if not reviews:
        click.echo("No new reviews found.")
        sys.exit(0)

    _print_reviews_table(reviews)

    append = since is not None and output_path.exists()
    _write_reviews_jsonl(reviews, output_path, append=append)

    if append:
        click.echo(click.style("Done! ", fg="green") + f"{len(reviews)} new reviews appended to {output_path}")
    else:
        click.echo(click.style("Done! ", fg="green") + f"{len(reviews)} reviews saved to {output_path}")
