# google-reviews-client

[![Release](https://img.shields.io/github/v/release/cauethenorio/google-reviews-client)](https://img.shields.io/github/v/release/cauethenorio/google-reviews-client)
[![Build status](https://img.shields.io/github/actions/workflow/status/cauethenorio/google-reviews-client/main.yml?branch=main)](https://github.com/cauethenorio/google-reviews-client/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/cauethenorio/google-reviews-client/branch/main/graph/badge.svg)](https://codecov.io/gh/cauethenorio/google-reviews-client)
[![License](https://img.shields.io/github/license/cauethenorio/google-reviews-client)](https://img.shields.io/github/license/cauethenorio/google-reviews-client)

A lightweight, non-official Python client for the Google Business Profile API — accounts, locations, and reviews.

> **Not affiliated with Google.** This library is a community project and not an official Google product.
> Google, Google Maps, and related marks are trademarks of Google LLC.

## Features

- **Typed data models** — `Account`, `Location`, `Review`, `Reviewer`, `ReviewReply` as Python dataclasses
- **Lazy pagination** — `list_reviews()` returns an iterator that fetches pages on demand, one review at a time
- **Incremental sync** — filter reviews by `update_time` to fetch only new or updated reviews
- **Auth-agnostic** — accepts any `google.auth.credentials.Credentials` (OAuth2, service account, etc.)
- **Typed exceptions** — `AuthenticationError`, `RateLimitError`, `NotFoundError` for granular error handling
- **CLI demo included** — fetch and save reviews from the terminal with a single command
- **Minimal dependencies** — only `httpx` and `google-auth` at runtime

## Prerequisites

Before using this library, you need a Google Cloud project with the Business Profile API enabled. This section walks you through the setup.

### 1. Create a Google Cloud project

Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project (or use an existing one).

### 2. Request access to the Business Profile API

The Google Business Profile API requires approval. Submit a request at:

https://developers.google.com/my-business/content/basic-setup

Fill out the form with your Google Cloud project details. Approval can take a few days to a couple of weeks.

### 3. Configure the OAuth consent screen

1. In the Cloud Console, go to **APIs & Services > OAuth consent screen**
2. Choose **External** user type
3. Fill in the required fields (app name, support email)
4. On the **Scopes** step, add the scope: `https://www.googleapis.com/auth/business.manage`
5. Add your Google account as a test user (while the app is in testing mode)

### 4. Create OAuth credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Choose **Desktop application** as the application type (for CLI usage) or **Web application** for server-side apps
4. Download the JSON file and save it as `credentials.json` in your working directory

### 5. Verify API access

Once your API access request is approved, you can verify it's working by running the CLI demo (see [Quick Start](#quick-start) below). If you see an `AuthenticationError`, your API access may not be approved yet.

## Installation

```bash
pip install google-reviews-client
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add google-reviews-client
```

To use the CLI demo, install with the `cli` extra:

```bash
pip install google-reviews-client[cli]
```

## Quick Start

### CLI Demo

The CLI demo authenticates via browser-based OAuth, fetches your reviews, prints them to the terminal, and saves them as JSON.

```bash
# Make sure credentials.json is in your current directory
google-reviews
```

On first run, a browser window opens for OAuth authorization. After granting consent, tokens are saved to `tokens.json` so subsequent runs don't require re-authentication.

You can also specify custom paths:

```bash
google-reviews /path/to/credentials.json /path/to/output.json
```

The CLI will prompt you to select an account and location if you have multiple, then fetch and display all reviews:

```
Fetching accounts...
Using account: My Business
Fetching locations...
Using location: locations/123456789

Fetching reviews for locations/123456789...

★★★★★ (5/5) - John Doe - 2024-01-15
  Great service and friendly staff!

★★★☆☆ (3/5) - Jane Smith - 2024-01-10
  Average experience, could be better.
  Reply: Thank you for your feedback!

---
Total reviews: 2
Saved to: reviews.json
```

### Programmatic Usage

```python
from google.oauth2.credentials import Credentials
from google_reviews_client import GoogleReviewsClient

# Create credentials (see "Authentication" section below)
creds = Credentials(
    token="your-access-token",
    refresh_token="your-refresh-token",
    token_uri="https://oauth2.googleapis.com/token",
    client_id="your-client-id",
    client_secret="your-client-secret",
)

client = GoogleReviewsClient(credentials=creds)

# Discover accounts and locations
accounts = client.list_accounts()
locations = client.list_locations(accounts[0].name)

# Fetch reviews (lazy iterator — pages fetched on demand)
for review in client.list_reviews(locations[0].full_name):
    print(f"{review.rating_value}/5 - {review.reviewer.display_name}")
    print(f"  {review.comment}")
```

## Authentication

The library accepts any `google.auth.credentials.Credentials` instance. Here are common ways to create credentials:

### From saved tokens

If you have OAuth2 tokens (e.g., from a previous authorization flow):

```python
from google.oauth2.credentials import Credentials

creds = Credentials(
    token="your-access-token",
    refresh_token="your-refresh-token",
    token_uri="https://oauth2.googleapis.com/token",
    client_id="your-client-id",
    client_secret="your-client-secret",
)
```

### From a service account

```python
from google.oauth2 import service_account

creds = service_account.Credentials.from_service_account_file(
    "service-account.json",
    scopes=["https://www.googleapis.com/auth/business.manage"],
)
```

### Browser-based OAuth flow

For interactive scripts, use `google-auth-oauthlib`:

```bash
pip install google-auth-oauthlib
```

```python
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    "credentials.json",
    scopes=["https://www.googleapis.com/auth/business.manage"],
)
creds = flow.run_local_server(port=0)
```

## Usage Examples

### List accounts and locations

```python
accounts = client.list_accounts()
for account in accounts:
    print(f"Account: {account.account_name} ({account.name})")

    locations = client.list_locations(account.name)
    for location in locations:
        print(f"  Location: {location.title} ({location.full_name})")
```

### Fetch all reviews

```python
for review in client.list_reviews(location.full_name):
    print(f"{review.rating_value}/5 by {review.reviewer.display_name}")
    print(f"  Posted: {review.create_time}")
    if review.comment:
        print(f"  Comment: {review.comment}")
    if review.has_reply:
        print(f"  Reply: {review.review_reply.comment}")
```

### Incremental sync

Fetch only reviews updated after a specific timestamp:

```python
from datetime import datetime, timezone

last_sync = datetime(2024, 1, 1, tzinfo=timezone.utc)

for review in client.list_reviews(location.full_name, update_time=last_sync):
    print(f"New/updated: {review.review_id} - {review.rating_value}/5")
```

### Error handling

```python
from google_reviews_client import (
    GoogleReviewsClient,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
)

try:
    reviews = list(client.list_reviews(location.full_name))
except AuthenticationError:
    print("Authentication failed. Check your credentials.")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds.")
except NotFoundError:
    print("Location not found. Check the location ID.")
```

### Serialize reviews to JSON

```python
import json

reviews = [review.to_dict() for review in client.list_reviews(location.full_name)]
with open("reviews.json", "w") as f:
    json.dump(reviews, f, indent=2, ensure_ascii=False)
```

## API Reference

### Client

| Method | Returns | Description |
|--------|---------|-------------|
| `list_accounts()` | `list[Account]` | Discover accessible Google Business accounts |
| `list_locations(account)` | `list[Location]` | List locations under an account |
| `list_reviews(location, *, update_time=None)` | `Iterator[Review]` | Fetch reviews with lazy pagination |

### Models

| Model | Key Fields |
|-------|------------|
| `Account` | `name`, `account_name`, `type` |
| `Location` | `location_id`, `account_id`, `title`, `full_name` (property) |
| `Review` | `review_id`, `star_rating`, `comment`, `create_time`, `update_time`, `reviewer`, `review_reply` |
| `Reviewer` | `display_name`, `profile_photo_url`, `is_anonymous` |
| `ReviewReply` | `comment`, `update_time` |
| `StarRating` | Enum: `ONE` through `FIVE` |

### Exceptions

| Exception | Trigger |
|-----------|---------|
| `GoogleReviewsError` | Base exception for all library errors |
| `AuthenticationError` | 401 — invalid or expired credentials |
| `PermissionError` | 403 — insufficient permissions |
| `NotFoundError` | 404 — resource not found |
| `RateLimitError` | 429 — rate limit exceeded (has `retry_after` attribute) |
| `GoogleAPIError` | 5xx — Google API server error |
| `ValidationError` | Invalid parameters |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

This project is licensed under the terms of the [MIT License](LICENSE).
