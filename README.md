# google-reviews-client

[![Release](https://img.shields.io/github/v/release/cauethenorio/google-reviews-client)](https://img.shields.io/github/v/release/cauethenorio/google-reviews-client)
[![Build status](https://img.shields.io/github/actions/workflow/status/cauethenorio/google-reviews-client/main.yml?branch=main)](https://github.com/cauethenorio/google-reviews-client/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/cauethenorio/google-reviews-client/branch/main/graph/badge.svg)](https://codecov.io/gh/cauethenorio/google-reviews-client)
[![License](https://img.shields.io/github/license/cauethenorio/google-reviews-client)](https://img.shields.io/github/license/cauethenorio/google-reviews-client)

A lightweight, non-official Python client for the Google Business Profile API: accounts, locations, and reviews.

> **Not affiliated with Google.** This library isn't an official Google product.
> Google, Google Maps, and related marks are trademarks of Google LLC.

## Features

- **Incremental sync** - fetch only new or updated reviews
- **Auth-agnostic** - accepts any `google.auth.credentials.Credentials` (OAuth2, service account, etc.)
- **CLI included** - fetch and save reviews from the terminal with a single command
- **Minimal dependencies** - only `httpx` and `google-auth` at runtime

## Prerequisites

Before you can use this project, you'll need:

1. **A Google Business Profile** - management access to a verified business listing on Google, active for at least 60
   days
2. **A Google Cloud project** - this is where your API credentials live
3. **API access approval** - Google requires a formal application, then you enable the APIs
4. **OAuth credentials** - configure the consent screen and download a JSON file for authentication

If you already have all of these, skip to [Installation](#installation). Otherwise, follow the steps below - they walk
you through everything.

### 1. Set up your Google Business Profile

You need to be an **owner or manager** of a verified business listing that's been **active for at least 60 days** before you can request API access.

**If you don't have a listing yet:**

1. Go to [business.google.com](https://business.google.com/) and sign in with your Google account
2. Click **Add your business to Google** and follow the prompts
3. Google will ask you to verify ownership - this usually happens via postcard, phone, or email
4. Wait for verification (up to 5 business days) and then **60 more days** before you can request API access

**If your business is already on Google Maps** but you haven't claimed it, search for it
on [Google Maps](https://maps.google.com), click your business, and select **Claim this business**.

### 2. Create a Google Cloud project

A Google Cloud project is a container for your API credentials. You don't need to pay anything - the free tier is
enough.

1. Go to [console.cloud.google.com/projectcreate](https://console.cloud.google.com/projectcreate)
2. Give it a name (e.g., "My Business Reviews") and click **Create**
3. Note your **project number** from the project dashboard - you'll need it in the next step

### 3. Get API access approval and enable the APIs

The Business Profile API is not open to everyone - Google reviews each application.

**Apply for access:**

1. Go to the [API access request form](https://support.google.com/business/contact/api_default)
2. Select **"Application for Basic API Access"** from the dropdown
3. Use the **same email** that's an owner or manager on your Business Profile
4. Enter your **project number** from step 2

> Applications are typically reviewed within 14 days. You can check your status in Cloud Console → APIs → Quotas for the
> Account Management API: **0 requests per minute** means pending, **300 requests per minute** means approved.

**After approval, enable these APIs** in the [API Library](https://console.cloud.google.com/apis/library):

1. **My Business Account Management API**
2. **My Business Business Information API**
3. **Google My Business API** (this is the reviews API)

> For each one: search by name → click on it → click **Enable**.

### 4. Set up OAuth credentials

You need to configure the OAuth consent screen (what users see when they log in) and create
a credentials file (what the CLI uses to start the authentication flow).

**Configure the consent screen:**

1. Go to [APIs & Services > OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)
2. Choose **External** user type and click **Create**
3. Fill in the **App name** (anything you like) and your **email address**
4. You can skip the **Scopes** step - the CLI requests the right scopes automatically
5. Under **Test users**, click **Add users** and enter your Google account email
6. Click **Save and Continue** through the remaining steps

> **Important:** You must add yourself as a test user. Without this, you'll get an "Access blocked" error when trying to
> log in.

**Create OAuth credentials:**

1. Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **Create Credentials > OAuth client ID**
3. Choose **Desktop application** as the application type
4. Give it a name (e.g., "Reviews CLI") and click **Create**
5. Click **Download JSON** and save the file in the directory where you'll run the CLI

> The downloaded file will be named something like `client_secret_123456.apps.googleusercontent.com.json` - the CLI
> auto-detects it, so you don't need to rename it.

## Installation

```bash
pip install google-reviews-client
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add google-reviews-client
```

To use the CLI, install with the `download-cli` extra:

```bash
pip install google-reviews-client[download-cli]
```

## Quick Start

### CLI

The CLI authenticates via browser-based OAuth, fetches your reviews, prints them to the terminal, and saves them as
JSONL.

```bash
# Auto-detect client secrets file in current directory
google-reviews

# Specify client secrets file explicitly
google-reviews --client-secrets-file /path/to/client_secret.json

# Use a specific tokens file (from a previous OAuth flow)
google-reviews --tokens-file /path/to/credentials.user@gmail.com.json

# Verbose mode - shows file search details and full error tracebacks
google-reviews -v
```

On first run, a browser window opens for Google OAuth. After granting consent, the CLI saves your tokens locally (e.g.,
`credentials.user@gmail.com.json`) so subsequent runs don't require re-authentication.

You can authenticate multiple Google accounts - each gets its own tokens file. If the CLI finds multiple tokens files,
it will ask you to specify which one to use.

The CLI will prompt you to select an account and location if you have multiple, then fetch and display all reviews:

```
google-reviews-client v0.1.0
Directory: /Users/you/reviews

Authenticated as Jane Smith (jane@example.com)
Tokens saved to credentials.jane@example.com.json
Fetching accounts...
  Using account: accounts/123 | Jane's Business
Fetching locations...
  Using location: locations/456 | My Coffee Shop

Fetching all reviews for My Coffee Shop...
  Date        Rating  Review                                                          Reply
  ---------------------------------------------------------------------------------------
  2024-01-15  5       Great service and friendly staff!                                No
  2024-01-10  3       Average experience, could be better.                             Yes

Done! 2 reviews saved to reviews-456.jsonl
```

On subsequent runs, if a `reviews-{location_id}.jsonl` file already exists, the CLI automatically syncs - fetching only
new or updated reviews and appending them to the file.

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

# Fetch reviews (lazy iterator - pages fetched on demand)
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

| Method                                        | Returns            | Description                                  |
|-----------------------------------------------|--------------------|----------------------------------------------|
| `list_accounts()`                             | `list[Account]`    | Discover accessible Google Business accounts |
| `list_locations(account)`                     | `list[Location]`   | List locations under an account              |
| `list_reviews(location, *, update_time=None)` | `Iterator[Review]` | Fetch reviews with lazy pagination           |

### Models

| Model         | Key Fields                                                                                      |
|---------------|-------------------------------------------------------------------------------------------------|
| `Account`     | `name`, `account_name`, `type`                                                                  |
| `Location`    | `location_id`, `account_id`, `title`, `full_name` (property)                                    |
| `Review`      | `review_id`, `star_rating`, `comment`, `create_time`, `update_time`, `reviewer`, `review_reply` |
| `Reviewer`    | `display_name`, `profile_photo_url`, `is_anonymous`                                             |
| `ReviewReply` | `comment`, `update_time`                                                                        |
| `StarRating`  | Enum: `ONE` through `FIVE`                                                                      |

### Exceptions

| Exception             | Trigger                                                 |
|-----------------------|---------------------------------------------------------|
| `GoogleReviewsError`  | Base exception for all library errors                   |
| `AuthenticationError` | 401 - invalid or expired credentials                    |
| `PermissionError`     | 403 - insufficient permissions                          |
| `NotFoundError`       | 404 - resource not found                                |
| `RateLimitError`      | 429 - rate limit exceeded (has `retry_after` attribute) |
| `GoogleAPIError`      | 5xx - Google API server error                           |
| `ValidationError`     | Invalid parameters                                      |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

This project is licensed under the terms of the [MIT License](LICENSE).
