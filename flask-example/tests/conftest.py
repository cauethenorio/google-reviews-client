"""Shared test fixtures for the Flask demo app."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from app import create_app
from cookies import TOKEN_COOKIE_NAME, encrypt_tokens  # noqa: F401

from google_reviews_client.models import (
    Account,
    Location,
    Review,
    Reviewer,
    ReviewReply,
    StarRating,
)

TEST_ENV = {
    "GOOGLE_CLIENT_ID": "test-client-id",
    "GOOGLE_CLIENT_SECRET": "test-client-secret",
    "SECRET_KEY": "test-secret-key-for-testing",
}


@pytest.fixture()
def env_vars(monkeypatch):
    """Set all required env vars for testing."""
    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)


@pytest.fixture()
def app(env_vars):
    """Create application for testing."""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture()
def fernet(app):
    """Get the Fernet instance from the app."""
    return app.config["FERNET"]


@pytest.fixture()
def authenticated_cookie(fernet):
    """Create an encrypted cookie with authenticated status."""
    token_data = {
        "auth_status": "authenticated",
        "access_token": "fake-access-token",
        "refresh_token": "fake-refresh-token",
        "expiry": "2099-01-01T00:00:00",
    }
    return encrypt_tokens(token_data, fernet)


@pytest.fixture()
def pending_cookie(fernet):
    """Create an encrypted cookie with pending auth status."""
    pending_data = {
        "auth_status": "pending",
        "state": "test-state-value",
        "verifier": "test-verifier-value",
    }
    return encrypt_tokens(pending_data, fernet)


@pytest.fixture()
def sample_accounts():
    """Sample Account objects for testing."""
    return [
        Account(name="accounts/111", account_name="Test Business", type="PERSONAL"),
        Account(name="accounts/222", account_name="Other Business", type="ORGANIZATION"),
    ]


@pytest.fixture()
def sample_locations():
    """Sample Location objects for testing."""
    return [
        Location(name="locations/aaa", location_id="aaa", account_id="111", title="Main Store", store_code="MAIN"),
        Location(name="locations/bbb", location_id="bbb", account_id="111", title="Branch Store", store_code=None),
    ]


@pytest.fixture()
def sample_reviews():
    """Sample Review objects for testing."""
    return [
        Review(
            review_id="r1",
            reviewer=Reviewer(display_name="Alice", profile_photo_url=None, is_anonymous=False),
            star_rating=StarRating.FIVE,
            comment="Great place!",
            create_time=datetime(2025, 3, 15, 10, 0),
            update_time=datetime(2025, 3, 15, 10, 0),
            review_reply=ReviewReply(comment="Thank you!", update_time=datetime(2025, 3, 16, 10, 0)),
        ),
        Review(
            review_id="r2",
            reviewer=Reviewer(display_name="Bob", profile_photo_url=None, is_anonymous=False),
            star_rating=StarRating.THREE,
            comment="It was okay. " * 20,
            create_time=datetime(2025, 2, 10, 10, 0),
            update_time=datetime(2025, 2, 10, 10, 0),
            review_reply=None,
        ),
    ]


@pytest.fixture()
def polish_reviews():
    """Reviews covering polish features: photo, anonymous, unspecified rating."""
    return [
        Review(
            review_id="p1",
            reviewer=Reviewer(
                display_name="Carol",
                profile_photo_url="https://lh3.googleusercontent.com/photo123",
                is_anonymous=False,
            ),
            star_rating=StarRating.FOUR,
            comment="Nice place!",
            create_time=datetime(2025, 4, 1, 10, 0),
            update_time=datetime(2025, 4, 1, 10, 0),
            review_reply=None,
        ),
        Review(
            review_id="p2",
            reviewer=Reviewer(display_name="Anonymous", profile_photo_url=None, is_anonymous=True),
            star_rating=StarRating.TWO,
            comment="Not great.",
            create_time=datetime(2025, 4, 2, 10, 0),
            update_time=datetime(2025, 4, 2, 10, 0),
            review_reply=None,
        ),
        Review(
            review_id="p3",
            reviewer=Reviewer(display_name="Dave", profile_photo_url=None, is_anonymous=False),
            star_rating=StarRating.STAR_RATING_UNSPECIFIED,
            comment="Left without rating.",
            create_time=datetime(2025, 4, 3, 10, 0),
            update_time=datetime(2025, 4, 3, 10, 0),
            review_reply=None,
        ),
    ]


@pytest.fixture()
def mock_client(sample_accounts, sample_locations):
    """Mock GoogleReviewsClient that returns sample data."""
    client = MagicMock()
    client.list_accounts.return_value = sample_accounts
    client.list_locations.return_value = sample_locations
    return client
