"""CLI demo for Google Business Reviews.

Usage:
    google-reviews [credentials_path] [output_path]

Requires the CLI extra: pip install google-business-reviews[cli]
"""

import json
import sys
from pathlib import Path

from .client import GoogleBusinessClient
from .exceptions import AuthenticationError, GoogleBusinessError

SCOPES = ["https://www.googleapis.com/auth/business.manage"]
DEFAULT_CREDENTIALS_PATH = "credentials.json"
DEFAULT_TOKENS_PATH = "tokens.json"
DEFAULT_OUTPUT_PATH = "reviews.json"


def _load_credentials(credentials_path: str, tokens_path: str):
    """Load credentials from token file or run OAuth flow."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("ERROR: google-auth-oauthlib is required for the CLI.")
        print("Install with: pip install google-business-reviews[cli]")
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
    creds_file = Path(credentials_path)
    if not creds_file.exists():
        print(f"ERROR: Credentials file not found: {credentials_path}")
        print()
        print("To set up credentials:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Create an OAuth 2.0 Client ID (Desktop application)")
        print("3. Download the JSON file and save it as 'credentials.json'")
        print()
        print("You also need to request access to the Google Business Profile API:")
        print("  https://developers.google.com/my-business/content/basic-setup")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: google-auth-oauthlib is required for the CLI.")
        print("Install with: pip install google-business-reviews[cli]")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes=SCOPES)
    creds = flow.run_local_server(port=0)
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
        print(f"No {label}s found.")
        sys.exit(1)

    if len(items) == 1:
        display = getattr(items[0], "account_name", items[0].name)
        print(f"Using {label}: {display}")
        return items[0]

    print(f"\nAvailable {label}s:")
    for i, item in enumerate(items, 1):
        display = getattr(item, "account_name", item.name)
        print(f"  {i}. {display}")

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
    print(f"{stars} ({review.rating_value}/5) - {review.reviewer.display_name} - {date_str}")
    if review.comment:
        print(f"  {review.comment}")
    if review.has_reply:
        print(f"  Reply: {review.review_reply.comment}")
    print()


def main() -> None:
    """CLI entry point for fetching Google Business reviews."""
    args = sys.argv[1:]
    credentials_path = args[0] if args else DEFAULT_CREDENTIALS_PATH
    output_path = args[1] if len(args) > 1 else DEFAULT_OUTPUT_PATH

    try:
        creds = _load_credentials(credentials_path, DEFAULT_TOKENS_PATH)
        client = GoogleBusinessClient(credentials=creds)

        # Discover account and location
        print("Fetching accounts...")
        accounts = client.list_accounts()
        account = _select_item(accounts, "account")

        print("Fetching locations...")
        locations = client.list_locations(account.name)
        location = _select_item(locations, "location")

        # Fetch reviews
        print(f"\nFetching reviews for {location.name}...\n")
        reviews_data = []
        for review in client.list_reviews(location.full_name):
            _print_review(review)
            reviews_data.append(review.to_dict())

        # Save to JSON
        Path(output_path).write_text(json.dumps(reviews_data, indent=2, ensure_ascii=False))
        print("---")
        print(f"Total reviews: {len(reviews_data)}")
        print(f"Saved to: {output_path}")

    except AuthenticationError:
        print("ERROR: Authentication failed.")
        print()
        print("Your API access may not be approved. To request access:")
        print("  https://developers.google.com/my-business/content/basic-setup")
        print()
        print("Make sure the Google Business Profile API is enabled in your project.")
        sys.exit(1)

    except GoogleBusinessError as e:
        print(f"ERROR: {e}")
        if e.body:
            print(f"Details: {e.body}")
        sys.exit(1)


if __name__ == "__main__":
    main()
