"""CLI for Google Reviews Client.

Usage:
    google-reviews                                    # auto-discover configs or first-time setup
    google-reviews --config-file /path/to/config.json # use a specific config
    google-reviews --client-secrets-file /path/to/secrets.json  # first-time setup
    google-reviews --language pt-BR                   # override review language
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

from .auth import (
    MultipleFilesFoundError,
    NotInstalledAppError,
    credentials_from_config_data,
    credentials_to_config_data,
    fetch_user_info,
    find_client_secrets_files,
    run_oauth_flow,
)
from .config import (
    Config,
    build_config_path,
    find_config_files,
    load_config,
    save_config,
)
from .logger import add_verbose_option

logger = logging.getLogger(__name__)
auth_logger = logging.getLogger("google_reviews_client.cli.auth")
http_logger = logging.getLogger("google_reviews_client.http_client.httpx_client")
config_logger = logging.getLogger("google_reviews_client.cli.config")


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


def first_time_setup(cwd: Path, client_secrets_file: Path | None) -> Config:
    """Run OAuth flow, prompt for accounts/locations, create config file."""
    path = find_client_secrets_files(cwd, explicit_path=client_secrets_file)
    creds = run_oauth_flow(path)

    user_info = fetch_user_info(creds)
    if user_info:
        name, email = user_info
        display = f"{name} ({email})" if name else email
        click.echo(click.style(f"Authenticated as {display}", fg="green"))
    else:
        email = click.prompt("Enter your email (for config filename)")

    project_number = extract_project_number(creds.client_id) or "default"
    client = GoogleReviewsClient(credentials=creds)

    click.echo()
    click.echo(click.style("Fetching accounts...", fg="cyan"))
    accounts = client.list_accounts()
    selected_accounts = select_multiple_items(accounts, "account", "{0.name} | {0.account_name}")

    targets = []
    for account in selected_accounts:
        click.echo()
        click.echo(click.style(f"Fetching locations for {account.account_name}...", fg="cyan"))
        locations = client.list_locations(account.name)
        selected_locations = select_multiple_items(locations, "location", "{0.name} | {0.title}")

        target = {
            "account": account.name,
            "account_name": account.account_name,
            "locations": [{"location": loc.name, "title": loc.title} for loc in selected_locations],
        }
        targets.append(target)

    config = Config(
        path=build_config_path(cwd, project_number, email),
        credentials_data=credentials_to_config_data(creds),
        targets=targets,
    )
    save_config(config)
    return config


def sync_target(
    client: GoogleReviewsClient,
    account_name: str,
    location_data: dict,
    user_specified_language: str | None,
    *,
    verbose: bool,  # noqa: ARG001
) -> None:
    """Sync reviews for a single location target."""
    location_id = location_data["location"].split("/")[-1]
    location_title = location_data.get("title", location_data["location"])
    full_name = location_data["location"]

    click.echo()
    click.echo(click.style(f"{account_name} > {location_title}", bold=True))

    output_path = Path(f"reviews-{location_id}.jsonl")
    existing_ids: set[str] = set()
    since: datetime | None = None
    if output_path.exists():
        existing_ids, since = read_jsonl_metadata(output_path)

    review_language = user_specified_language or location_data.get("language")
    if review_language:
        logger.debug("Using language: %s", review_language)

    if since is not None:
        click.echo(click.style(f"Syncing reviews since {since.isoformat()}...", fg="cyan"))
    else:
        click.echo(click.style("Fetching all reviews...", fg="cyan"))

    print_reviews_table_header()
    reviews: list = []
    for review in client.list_reviews(full_name, since=since, language=review_language):
        print_review_row(review)
        reviews.append(review)

    logger.debug("Received %d reviews from API", len(reviews))

    if not reviews:
        click.echo("  (no new reviews)")
        return

    click.echo()

    if since is not None:
        new_count, updated_count = sync_reviews_jsonl(reviews, output_path, existing_ids)
        parts = []
        if new_count:
            parts.append(f"{new_count} new")
        if updated_count:
            parts.append(f"{updated_count} updated")
        click.echo(click.style("Done! ", fg="green") + f"{' and '.join(parts)} reviews saved to {output_path}")
    else:
        write_reviews_jsonl(reviews, output_path)
        click.echo(click.style("Done! ", fg="green") + f"{len(reviews)} reviews saved to {output_path}")

    if user_specified_language and user_specified_language != location_data.get("language"):
        location_data["language"] = user_specified_language


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--client-secrets-file",
    help="Path to OAuth client secrets JSON file (for first-time setup).",
    default=None,
    type=click.Path(exists=True, file_okay=True, readable=True, path_type=Path),
)
@click.option(
    "--config-file",
    help="Path to a specific config file to use.",
    default=None,
    type=click.Path(exists=True, file_okay=True, readable=True, path_type=Path),
)
@click.option(
    "--language",
    "user_specified_language",
    help="Language for reviews (e.g., 'pt-BR'). Saved per-location in config.",
    default=None,
)
@add_verbose_option([logger, auth_logger, http_logger, config_logger])
def main(client_secrets_file, config_file, user_specified_language, verbose):
    """Download all your Google Business reviews."""

    print_banner()
    cwd = Path.cwd()

    # --- Find or create config files ---
    config_files = find_config_files(cwd, explicit_path=config_file)

    if not config_files:
        try:
            config = first_time_setup(cwd, client_secrets_file)
        except FileNotFoundError as e:
            click.echo(click.style("ERROR: ", fg="red") + str(e) + "\n")
            click.echo("To set up credentials:")
            click.echo("1. Go to https://console.cloud.google.com/apis/credentials")
            click.echo("2. Create an OAuth 2.0 Client ID (Desktop application)")
            click.echo("3. Download the JSON file to this directory")
            sys.exit(1)
        except MultipleFilesFoundError as e:
            click.echo(click.style("ERROR: ", fg="red") + "Multiple client secrets files found:")
            for path in e.files_found:
                click.echo(f"  {click.style(path.name, fg='yellow')}")
            prog = Path(sys.argv[0]).name
            click.echo("\nSpecify which file to use:")
            click.echo(f"  {prog} --client-secrets-file <path>")
            sys.exit(1)
        except NotInstalledAppError:
            click.echo(click.style("ERROR: ", fg="red") + "Only desktop (installed) app credentials are supported.\n")
            click.echo("Your client secrets file uses 'web' type credentials.")
            click.echo("To fix this:")
            click.echo("1. Go to https://console.cloud.google.com/apis/credentials")
            click.echo("2. Create an OAuth 2.0 Client ID with type 'Desktop app'")
            click.echo("3. Download the new JSON file to this directory")
            sys.exit(1)
        configs = [config]
    else:
        configs = [load_config(path) for path in config_files]

    # --- Process each config ---
    for config in configs:
        click.echo(click.style(f"\nUsing config: {config.path.name}", dim=True))

        try:
            creds = credentials_from_config_data(config.credentials_data)
        except Exception:
            click.echo(click.style("ERROR: ", fg="red") + f"Invalid credentials in {config.path.name}")
            click.echo("Delete this config file and re-run to re-authenticate.")
            if verbose:
                logger.exception("Credentials error")
            continue

        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request

            try:
                creds.refresh(Request())
                config.credentials_data = credentials_to_config_data(creds)
                save_config(config)
            except Exception:
                click.echo(click.style("ERROR: ", fg="red") + f"Failed to refresh credentials in {config.path.name}")
                click.echo("Delete this config file and re-run to re-authenticate.")
                if verbose:
                    logger.exception("Refresh error")
                continue

        if not config.targets:
            click.echo("No targets configured. Fetching accounts...")
            client = GoogleReviewsClient(credentials=creds)
            accounts = client.list_accounts()
            selected_accounts = select_multiple_items(accounts, "account", "{0.name} | {0.account_name}")

            for account in selected_accounts:
                click.echo(click.style(f"Fetching locations for {account.account_name}...", fg="cyan"))
                locations = client.list_locations(account.name)
                selected_locations = select_multiple_items(locations, "location", "{0.name} | {0.title}")

                config.targets.append({
                    "account": account.name,
                    "account_name": account.account_name,
                    "locations": [{"location": loc.name, "title": loc.title} for loc in selected_locations],
                })
            save_config(config)

        client = GoogleReviewsClient(credentials=creds)

        for target in config.targets:
            account_name = target.get("account_name", target["account"])
            for location_data in target.get("locations", []):
                try:
                    sync_target(client, account_name, location_data, user_specified_language, verbose=verbose)
                except RateLimitError as e:
                    print_quota_error(e, verbose=verbose, project_number=extract_project_number(creds.client_id))
                except AuthenticationError:
                    click.echo(click.style("\nERROR: ", fg="red") + "Authentication failed.")
                    click.echo("Your API access may not be approved.")
                    if verbose:
                        logger.exception("Authentication error")
                    break
                except GoogleReviewsError as e:
                    print_api_error(e, verbose=verbose)

        save_config(config)
