"""API helpers: credential reconstruction and single-page review fetch."""

from datetime import datetime

from cookies import TOKEN_COOKIE_NAME, decrypt_tokens
from flask import current_app, request
from google.oauth2.credentials import Credentials

from google_reviews_client.client import GoogleReviewsClient


def get_client():
    """Reconstruct credentials from cookie and return a GoogleReviewsClient."""
    cookie = request.cookies.get(TOKEN_COOKIE_NAME)
    data = decrypt_tokens(cookie, current_app.config["FERNET"])
    if data is None or data.get("auth_status") != "authenticated":
        return None

    creds = Credentials(
        token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=current_app.config["GOOGLE_CLIENT_ID"],
        client_secret=current_app.config["GOOGLE_CLIENT_SECRET"],
        expiry=datetime.fromisoformat(data["expiry"]) if data.get("expiry") else None,
    )
    return GoogleReviewsClient(creds)


def get_reviews_page(client, location_name, page_token=None, language=None, page_size=50):
    """Fetch a single page of reviews using the client's public API."""
    if language:
        language = language.strip()
    page = client.get_reviews_page(location_name, page_token=page_token, page_size=page_size, language=language)
    return page.reviews, page.next_page_token, page.total_review_count, page.average_rating


def get_all_reviews(client, location_name, language=None):
    """Fetch all reviews by paginating through all pages."""
    all_reviews = []
    page_token = None
    while True:
        reviews, next_token, _, _ = get_reviews_page(client, location_name, page_token, language=language)
        all_reviews.extend(reviews)
        if not next_token:
            break
        page_token = next_token
    return all_reviews
