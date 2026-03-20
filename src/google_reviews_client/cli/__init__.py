"""CLI for Google Reviews Client.

Usage:
    google-reviews                                    # auto-detect credentials
    google-reviews --client-secrets-file /path/to/secrets.json
    google-reviews --tokens-file /path/to/tokens.json
    google-reviews -v                                 # verbose mode
"""

import json
import logging
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import click

from google_reviews_client.client import GoogleReviewsClient
from google_reviews_client.exceptions import (
    AuthenticationError,
    GoogleReviewsError,
    RateLimitError,
)
from google_reviews_client.exceptions import (
    PermissionError as APIPermissionError,
)

from .auth import (
    MultipleFilesFoundError,
    NoFilesFoundError,
    NotInstalledAppError,
    fetch_user_info,
    find_client_secrets_files,
    find_tokens_files,
    load_tokens,
    run_oauth_flow,
    save_tokens,
)
from .logger import add_verbose_option

logger = logging.getLogger(__name__)
auth_logger = logging.getLogger("google_reviews_client.cli.auth")
http_logger = logging.getLogger("google_reviews_client.http_client.httpx_client")


def get_version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("google-reviews-client")
    except PackageNotFoundError:
        return "dev"


def print_banner() -> None:
    click.echo(click.style(f"google-reviews-client v{get_version()}", bold=True))
    click.echo(click.style(f"Directory: {Path.cwd()}", dim=True))
    click.echo()


def select_item(items: list, label: str, format_str: str):
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


def select_multiple_items(items: list, label: str, format_str: str) -> list:
    """Let user multi-select from a list. Auto-select if only one.

    Accepts comma-separated numbers or 'a' for all.
    Returns list of selected items.
    """
    if not items:
        return []

    if len(items) == 1:
        display = format_str.format(items[0])
        click.echo(f"  Using {label}: {display}")
        return items

    click.echo(click.style(f"\nAvailable {label}s:", bold=True))
    for i, item in enumerate(items, 1):
        display = format_str.format(item)
        click.echo(f"  {click.style(f'{i}.', dim=True)} {display}")
    click.echo(f"  {click.style('a.', dim=True)} All {label}s")

    while True:
        choice = click.prompt(f"\nSelect {label}s (e.g., 1,2 or a)").strip().lower()
        if choice == "a":
            return list(items)
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
            if all(0 <= idx < len(items) for idx in indices):
                return [items[idx] for idx in indices]
        except ValueError:
            pass
        click.echo(f"Invalid choice. Enter numbers 1-{len(items)} separated by commas, or 'a' for all.")


def display_width(text: str) -> int:
    """Return the number of terminal columns a string occupies."""
    width = 0
    for ch in text:
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ("W", "F") else 1
    return width


def truncate_to_width(text: str, max_width: int) -> str:
    """Truncate a string to fit in max_width terminal columns, adding '...' if truncated."""
    width = 0
    for i, ch in enumerate(text):
        eaw = unicodedata.east_asian_width(ch)
        char_width = 2 if eaw in ("W", "F") else 1
        if width + char_width > max_width - 3:
            return text[:i] + "..."
        width += char_width
    return text


def pad_to_width(text: str, target_width: int) -> str:
    """Pad a string with spaces to fill target_width terminal columns."""
    current = display_width(text)
    return text + " " * max(target_width - current, 0)


STARS_DISPLAY_WIDTH = 11  # 5 stars x 2 columns each + 1 space
REVIEWER_WIDTH = 20
FIXED_COLS_WIDTH = 12 + STARS_DISPLAY_WIDTH + REVIEWER_WIDTH + 7  # date + stars + reviewer + replied
MIN_COMMENT_WIDTH = 20


def get_comment_width() -> int:
    term_width = shutil.get_terminal_size().columns
    return max(term_width - FIXED_COLS_WIDTH, MIN_COMMENT_WIDTH)


def format_stars(rating: int) -> str:
    return "\u2b50" * rating + "  " * (5 - rating) + " "


def print_reviews_table_header() -> None:
    comment_width = get_comment_width()
    rating_padding = " " * (STARS_DISPLAY_WIDTH - 6)  # 6 = len("Rating")
    header = f"{'Date':<12}Rating{rating_padding}{'Review':<{comment_width}}{'Reviewer':<{REVIEWER_WIDTH}}Replied"
    click.echo(click.style(header, bold=True))
    click.echo("-" * (FIXED_COLS_WIDTH + comment_width))


def print_review_row(review) -> None:
    comment_width = get_comment_width()
    comment = review.comment.replace("\n", " ")
    comment = truncate_to_width(comment, comment_width)
    comment = pad_to_width(comment, comment_width)
    date_str = review.create_time.strftime("%Y-%m-%d")
    stars = format_stars(review.rating_value)
    reviewer = truncate_to_width(review.reviewer.display_name, REVIEWER_WIDTH)
    reviewer = pad_to_width(reviewer, REVIEWER_WIDTH)
    reply = "Yes" if review.has_reply else "No"
    click.echo(f"{date_str:<12}{stars}{comment}{reviewer}{reply}")


def read_jsonl_metadata(path: Path) -> tuple[set[str], datetime | None]:
    """Read a JSONL file and return (set of review_ids, max update_time).

    Streams through the file without loading all review data into memory.
    """
    review_ids: set[str] = set()
    max_update_time: datetime | None = None
    with path.open() as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if not stripped:
                continue
            review_dict = json.loads(stripped)
            review_ids.add(review_dict["review_id"])
            ut = datetime.fromisoformat(review_dict["update_time"])
            if max_update_time is None or ut > max_update_time:
                max_update_time = ut
    logger.debug("Existing JSONL: %d reviews, latest update: %s", len(review_ids), max_update_time)
    return review_ids, max_update_time


def write_reviews_jsonl(reviews: list, path: Path) -> None:
    """Write reviews to a JSONL file (overwrite)."""
    with path.open("w") as f:
        for review in reviews:
            f.write(json.dumps(review.to_dict(), ensure_ascii=False) + "\n")


def sync_reviews_jsonl(reviews: list, path: Path, existing_ids: set[str]) -> tuple[int, int]:
    """Sync fetched reviews into an existing JSONL file.

    New reviews are appended. Updated reviews (same ID, newer data)
    are replaced by streaming to a temp file and renaming.

    Returns (new_count, updated_count).
    """
    new_reviews = [r for r in reviews if r.review_id not in existing_ids]
    updated_reviews = {r.review_id: r for r in reviews if r.review_id in existing_ids}

    logger.debug(
        "Sync: %d fetched, %d new, %d updated, %d unchanged",
        len(reviews),
        len(new_reviews),
        len(updated_reviews),
        len(reviews) - len(new_reviews) - len(updated_reviews),
    )

    if updated_reviews:
        # Stream original to temp, replacing updated lines
        tmp_path = path.with_suffix(".jsonl.tmp")
        with path.open() as src, tmp_path.open("w") as dst:
            for raw_line in src:
                stripped = raw_line.strip()
                if not stripped:
                    continue
                review_dict = json.loads(stripped)
                rid = review_dict["review_id"]
                if rid in updated_reviews:
                    dst.write(json.dumps(updated_reviews[rid].to_dict(), ensure_ascii=False) + "\n")
                else:
                    dst.write(raw_line)
            # Append new reviews at the end
            for review in new_reviews:
                dst.write(json.dumps(review.to_dict(), ensure_ascii=False) + "\n")
        tmp_path.rename(path)
    elif new_reviews:
        # No updates, just append
        with path.open("a") as f:
            for review in new_reviews:
                f.write(json.dumps(review.to_dict(), ensure_ascii=False) + "\n")

    return len(new_reviews), len(updated_reviews)


def extract_project_number(client_id: str | None) -> str | None:
    """Extract project number from client_id (e.g., '724219465644-xxx.apps.googleusercontent.com' -> '724219465644')."""
    if not client_id:
        return None
    parts = client_id.split("-", 1)
    return parts[0] if parts[0].isdigit() else None


def terminal_link(url: str, text: str) -> str:
    """Create a clickable terminal hyperlink using OSC 8."""
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def print_quota_error(e: RateLimitError, *, verbose: bool, project_number: str | None = None) -> None:
    """Print a helpful message for quota errors, which usually mean API access hasn't been approved."""
    click.echo(click.style("\nERROR: ", fg="red") + "API quota exceeded.\n")
    click.echo("This usually means your Google Cloud project hasn't been approved for")
    click.echo("Business Profile API access yet.\n")

    access_url = "https://support.google.com/business/contact/api_default"
    click.echo("To request access:")
    click.echo(f"1. Go to {terminal_link(access_url, click.style('API access request form', fg='cyan'))}")
    click.echo("2. Select 'Application for Basic API Access'")
    click.echo("3. Use the email that's an owner or manager on your Business Profile\n")

    project_param = f"?project={project_number}" if project_number else ""
    acct_mgmt_url = (
        f"https://console.cloud.google.com/apis/api/mybusinessaccountmanagement.googleapis.com{project_param}"
    )
    gmb_url = f"https://console.cloud.google.com/apis/api/mybusiness.googleapis.com{project_param}"
    click.echo("After approval, make sure these APIs are enabled in your project:")
    click.echo(f"  - {terminal_link(acct_mgmt_url, click.style('My Business Account Management API', fg='cyan'))}")
    click.echo(f"  - {terminal_link(gmb_url, click.style('Google My Business API', fg='cyan'))}\n")

    click.echo("You can check your status in Cloud Console > APIs > Quotas:")
    click.echo("  0 requests/min = pending, 300 requests/min = approved")
    if verbose:
        logger.exception("Quota error details: %s", e)


def print_api_error(e: GoogleReviewsError, *, verbose: bool) -> None:
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


def resolve_credentials(cwd: Path, tokens_file: Path | None, client_secrets_file: Path | None):
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

    # Fetch user info for greeting and email-based filename
    email = None
    user_info = fetch_user_info(creds)
    if user_info:
        name, email = user_info
        display = f"{name} ({email})" if name else email
        click.echo(click.style(f"Authenticated as {display}", fg="green"))

    save_tokens(cwd, creds, email=email)
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
@click.option(
    "--language",
    "user_specified_language",
    help="Language for reviews (e.g., 'pt-BR'). Auto-detected from location if not specified.",
    default=None,
)
@add_verbose_option([logger, auth_logger, http_logger])
def main(client_secrets_file, tokens_file, user_specified_language, verbose):
    """Download all your Google Business reviews."""

    print_banner()
    cwd = Path.cwd()

    # --- Resolve credentials ---
    try:
        creds = resolve_credentials(cwd, tokens_file, client_secrets_file)
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
        click.echo()
        click.echo(click.style("Fetching accounts...", fg="cyan"))
        accounts = client.list_accounts()
        account = select_item(accounts, "account", "{0.name} | {0.account_name}")

        click.echo()
        click.echo(click.style("Fetching locations...", fg="cyan"))
        locations = client.list_locations(account.name)
        location = select_item(locations, "location", "{0.name} | {0.title}")
    except AuthenticationError:
        click.echo(click.style("\nERROR: ", fg="red") + "Authentication failed.\n")
        click.echo("Your API access may not be approved. To request access:")
        click.echo("  https://developers.google.com/my-business/content/basic-setup\n")
        click.echo("Make sure the Google Business Profile API is enabled in your project.")
        if verbose:
            logger.exception("Authentication error details")
        sys.exit(1)
    except RateLimitError as e:
        print_quota_error(e, verbose=verbose, project_number=extract_project_number(creds.client_id))
        sys.exit(1)
    except APIPermissionError as e:
        print_api_error(e, verbose=verbose)
        sys.exit(1)
    except GoogleReviewsError as e:
        print_api_error(e, verbose=verbose)
        sys.exit(1)

    # --- Fetch and save reviews ---
    output_path = Path(f"reviews-{location.location_id}.jsonl")
    existing_ids: set[str] = set()
    since: datetime | None = None
    if output_path.exists():
        existing_ids, since = read_jsonl_metadata(output_path)

    review_language = None
    if user_specified_language:
        review_language = user_specified_language
        click.echo(click.style(f"\nSelected language for reviews: {review_language} (from --language flag)", dim=True))

    elif location.language:
        review_language = location.language
        click.echo(click.style(f"\nSelected language for reviews: {review_language} (from location).", dim=True))
        click.echo(click.style("Use --language to override if reviews are translated.", dim=True))

    if since is not None:
        click.echo(click.style(f"Syncing reviews since {since.isoformat()}...", fg="cyan"))
    else:
        click.echo(click.style(f"Fetching all reviews for {location.title}...", fg="cyan"))

    print_reviews_table_header()
    reviews: list = []
    try:
        for review in client.list_reviews(location.full_name, since=since, language=review_language):
            print_review_row(review)
            reviews.append(review)
    except RateLimitError as e:
        print_quota_error(e, verbose=verbose, project_number=extract_project_number(creds.client_id))
        sys.exit(1)
    except GoogleReviewsError as e:
        print_api_error(e, verbose=verbose)
        sys.exit(1)

    logger.debug("Received %d reviews from API", len(reviews))

    if not reviews:
        click.echo("  (no new reviews)")
        sys.exit(0)

    click.echo()

    if since is not None:
        new_count, updated_count = sync_reviews_jsonl(reviews, output_path, existing_ids)
        click.echo()
        parts = []
        if new_count:
            parts.append(f"{new_count} new")
        if updated_count:
            parts.append(f"{updated_count} updated")
        click.echo(click.style("Done! ", fg="green") + f"{' and '.join(parts)} reviews saved to {output_path}")
    else:
        write_reviews_jsonl(reviews, output_path)
        click.echo()
        click.echo(click.style("Done! ", fg="green") + f"{len(reviews)} reviews saved to {output_path}")
