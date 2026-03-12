"""CLI demo for Google Business Reviews.

Usage:
    google-reviews                              # auto-detect credentials
    google-reviews -c /path/to/credentials.json # explicit credentials
    google-reviews -o output.json               # custom output path

Requires the CLI extra: pip install google-reviews-client[cli]
"""

import argparse
import errno
import json
import sys
import urllib.parse
from pathlib import Path

from .client import GoogleReviewsClient
from .exceptions import AuthenticationError, GoogleReviewsError

SCOPES = ["https://www.googleapis.com/auth/business.manage"]
DEFAULT_TOKENS_PATH = "tokens.json"
DEFAULT_OUTPUT_PATH = "reviews.json"

_CREDENTIAL_GLOBS = ("credentials.json", "client_secret*.json", "*_client_secret*.json")
_LOCALHOST_HOSTS = frozenset(("localhost", "127.0.0.1", "::1"))
_OOB_URI = "urn:ietf:wg:oauth:2.0:oob"

# ANSI escape codes for terminal colors
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_RESET = "\033[0m"


def _get_version() -> str:
    """Return the installed package version, or 'dev' if not installed."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("google-reviews-client")
    except PackageNotFoundError:
        return "dev"


def _print_banner(credentials_path: Path, how_found: str, credential_type: str, ports: list[int]) -> None:
    """Print the startup info banner."""
    print(f"{_BOLD}google-reviews-client{_RESET} {_DIM}v{_get_version()}{_RESET}")
    print(f"{_CYAN}Credentials:{_RESET} {credentials_path} ({how_found})")
    type_label = "Desktop" if credential_type == "installed" else "Web"
    print(f"{_CYAN}Type:{_RESET} {type_label} ({credential_type})")
    if ports:
        port_str = str(ports[0])
        if len(ports) > 1:
            fallbacks = ", ".join(str(p) for p in ports[1:])
            port_str += f" (fallback: {fallbacks})"
        print(f"{_CYAN}OAuth port:{_RESET} {port_str}")
    print()


def _find_credentials_file() -> Path:
    """Search cwd for a credentials file using common glob patterns.

    Returns the path if exactly one match is found. Exits with an error
    if zero or multiple matches are found.
    """
    cwd = Path.cwd()
    matches: set[Path] = set()
    for pattern in _CREDENTIAL_GLOBS:
        matches.update(cwd.glob(pattern))

    if len(matches) == 1:
        return matches.pop()

    if len(matches) == 0:
        print(f"{_RED}ERROR:{_RESET} No credentials file found in the current directory.")
        print()
        print("To set up credentials:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Create an OAuth 2.0 Client ID (Desktop application)")
        print("3. Download the JSON file and save it as 'credentials.json'")
        print()
        print("Expected file names: credentials.json, client_secret*.json")
        print()
        print("You also need to request access to the Google Business Profile API:")
        print("  https://developers.google.com/my-business/content/basic-setup")
        sys.exit(1)

    # Multiple matches
    print(f"{_RED}ERROR:{_RESET} Multiple credential files found:")
    for path in sorted(matches):
        print(f"  {_YELLOW}{path}{_RESET}")
    print()
    print("Specify which file to use:")
    print("  google-reviews -c <path>")
    sys.exit(1)


def _parse_oauth_config(credentials_path: Path) -> tuple[str, list[int], list[str]]:
    """Parse credentials JSON and extract credential type, localhost ports, and redirect URIs.

    Returns (credential_type, ports, redirect_uris) where credential_type is 'installed'
    or 'web', ports is a list of all localhost ports found (may be empty), and redirect_uris
    is the raw list from the credentials file.
    Exits only if the file structure is invalid (missing 'installed'/'web' key).
    """
    data = json.loads(credentials_path.read_text())

    # Find the credential config (installed or web)
    config = data.get("installed") or data.get("web")
    if not config:
        print(f"{_RED}ERROR:{_RESET} Invalid credentials file — missing 'installed' or 'web' key.")
        print(f"  File: {credentials_path}")
        sys.exit(1)

    credential_type = "installed" if "installed" in data else "web"
    redirect_uris = config.get("redirect_uris", [])

    # Collect all localhost ports
    ports: list[int] = []
    for uri in redirect_uris:
        parsed = urllib.parse.urlparse(uri)
        hostname = parsed.hostname
        if hostname in _LOCALHOST_HOSTS:
            if parsed.port is not None:
                ports.append(parsed.port)
            else:
                default_ports = {"http": 80, "https": 443}
                ports.append(default_ports.get(parsed.scheme, 80))

    return credential_type, ports, redirect_uris


def _validate_ports(ports: list[int], redirect_uris: list[str], credential_type: str) -> None:
    """Validate that ports are available for OAuth. Exits if no usable ports found."""
    if ports:
        return

    if _OOB_URI in redirect_uris:
        print(f"{_RED}ERROR:{_RESET} Your credentials use the OOB redirect flow (urn:ietf:wg:oauth:2.0:oob)")
        print("which is no longer supported by Google.")
        print()
        print("To fix this:")
        print("1. Go to APIs & Services > Credentials in the Google Cloud Console")
        print("2. Edit your OAuth client ID")
        print("3. Add http://localhost as an authorized redirect URI")
        print("4. Download the updated credentials JSON")
        sys.exit(1)

    if credential_type == "web":
        print(f"{_RED}ERROR:{_RESET} Web credentials require a localhost redirect URI for the CLI.")
        print()
        print("To fix this:")
        print("1. Go to APIs & Services > Credentials in the Google Cloud Console")
        print("2. Edit your OAuth client ID")
        print("3. Add http://localhost:<port> as an authorized redirect URI")
        print("4. Download the updated credentials JSON")
        sys.exit(1)

    print(f"{_RED}ERROR:{_RESET} No supported redirect URI found in credentials file.")
    print(f"  redirect_uris: {redirect_uris}")
    print()
    print("Expected: http://localhost or http://localhost:<port>")
    sys.exit(1)


def _run_oauth_flow(credentials_path: Path, ports: list[int], redirect_uris: list[str], credential_type: str):
    """Run the OAuth installed app flow with port retry and return credentials."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print(f"{_RED}ERROR:{_RESET} google-auth-oauthlib is required for the CLI.")
        print("Install with: pip install google-reviews-client[cli]")
        sys.exit(1)

    _validate_ports(ports, redirect_uris, credential_type)

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes=SCOPES)

    failed_ports: list[int] = []
    for i, port in enumerate(ports):
        try:
            return flow.run_local_server(port=port)
        except OSError as e:
            if e.errno != errno.EADDRINUSE:
                raise
            failed_ports.append(port)
            if i + 1 < len(ports):
                print(f"{_YELLOW}Port {port} is in use, trying {ports[i + 1]}...{_RESET}")

    # All ports failed
    port_list = ", ".join(str(p) for p in failed_ports)
    print(f"{_RED}ERROR:{_RESET} Could not start OAuth callback server.")
    if len(failed_ports) == 1:
        print(f"  Port {port_list} is already in use.")
        print("  Free the port and try again.")
    else:
        print(f"  All configured ports are in use: {port_list}")
        print("  Free one of these ports and try again.")
    sys.exit(1)


def _load_credentials(
    credentials_path: Path, tokens_path: str, ports: list[int], redirect_uris: list[str], credential_type: str
):
    """Load credentials from token file or run OAuth flow."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        print(f"{_RED}ERROR:{_RESET} google-auth-oauthlib is required for the CLI.")
        print("Install with: pip install google-reviews-client[cli]")
        sys.exit(1)

    # Try loading existing tokens
    token_file = Path(tokens_path)
    if token_file.exists():
        token_data = json.loads(token_file.read_text())
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes"),
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_tokens(creds, tokens_path)
        return creds

    # No tokens — run OAuth flow
    creds = _run_oauth_flow(credentials_path, ports, redirect_uris, credential_type)
    _save_tokens(creds, tokens_path)
    return creds


def _save_tokens(creds, tokens_path: str) -> None:
    """Persist credentials to token file."""
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else [],
    }
    Path(tokens_path).write_text(json.dumps(token_data, indent=2))


def _select_item(items: list, label: str):
    """Let user select from a list, auto-select if only one."""
    if not items:
        print(f"{_RED}ERROR:{_RESET} No {label}s found.")
        sys.exit(1)

    if len(items) == 1:
        display = getattr(items[0], "account_name", items[0].name)
        print(f"  {_CYAN}Using {label}:{_RESET} {display}")
        return items[0]

    print(f"\n{_BOLD}Available {label}s:{_RESET}")
    for i, item in enumerate(items, 1):
        display = getattr(item, "account_name", item.name)
        print(f"  {_DIM}{i}.{_RESET} {display}")

    while True:
        choice = input(f"\nSelect {label} (1-{len(items)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
        except ValueError:
            pass
        print(f"Invalid choice. Enter a number between 1 and {len(items)}.")


def _print_review(review) -> None:
    """Print a single review to the terminal."""
    stars = "\u2605" * review.rating_value + "\u2606" * (5 - review.rating_value)
    date_str = review.create_time.strftime("%Y-%m-%d")
    print(
        f"  {_BOLD}{stars} ({review.rating_value}/5){_RESET} - {review.reviewer.display_name} - {_DIM}{date_str}{_RESET}"
    )
    if review.comment:
        print(f"    {review.comment}")
    if review.has_reply:
        print(f"    {_CYAN}Reply:{_RESET} {review.review_reply.comment}")
    print()


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="google-reviews",
        description="Fetch Google Business Profile reviews and save as JSON",
    )
    parser.add_argument(
        "-c",
        "--credentials",
        type=Path,
        default=None,
        help="path to OAuth credentials JSON file (auto-detected if not specified)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"path for JSON output file (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser


def main() -> None:
    """CLI entry point for fetching Google Business reviews."""
    parser = _build_parser()
    args = parser.parse_args()

    # Resolve credentials path
    if args.credentials is not None:
        credentials_path = args.credentials
        how_found = "specified via -c"
        if not credentials_path.exists():
            print(f"{_RED}ERROR:{_RESET} Credentials file not found: {credentials_path}")
            print()
            print("Check the path and try again, or omit -c to auto-detect.")
            sys.exit(1)
    else:
        credentials_path = _find_credentials_file()
        how_found = "auto-detected"

    # Parse OAuth config and print banner
    credential_type, ports, redirect_uris = _parse_oauth_config(credentials_path)

    _print_banner(credentials_path, how_found, credential_type, ports)

    output_path = args.output

    try:
        creds = _load_credentials(credentials_path, DEFAULT_TOKENS_PATH, ports, redirect_uris, credential_type)
        client = GoogleReviewsClient(credentials=creds)

        # Discover account and location
        print(f"{_CYAN}Fetching accounts...{_RESET}")
        accounts = client.list_accounts()
        account = _select_item(accounts, "account")

        print(f"{_CYAN}Fetching locations...{_RESET}")
        locations = client.list_locations(account.name)
        location = _select_item(locations, "location")

        # Fetch reviews
        print(f"\n{_CYAN}Fetching reviews for {location.name}...{_RESET}\n")
        reviews_data = []
        for review in client.list_reviews(location.full_name):
            _print_review(review)
            reviews_data.append(review.to_dict())

        # Save to JSON
        output_path.write_text(json.dumps(reviews_data, indent=2, ensure_ascii=False))
        print(f"\n{_GREEN}Done!{_RESET} {len(reviews_data)} reviews saved to {output_path}")

    except AuthenticationError:
        print(f"{_RED}ERROR:{_RESET} Authentication failed.")
        print()
        print("Your API access may not be approved. To request access:")
        print("  https://developers.google.com/my-business/content/basic-setup")
        print()
        print("Make sure the Google Business Profile API is enabled in your project.")
        sys.exit(1)

    except GoogleReviewsError as e:
        print(f"{_RED}ERROR:{_RESET} {e}")
        if e.body:
            print(f"  Details: {e.body}")
        sys.exit(1)


if __name__ == "__main__":
    main()
