"""API helpers: credential reconstruction and single-page review fetch."""

from datetime import datetime

from cookies import TOKEN_COOKIE_NAME, decrypt_tokens
from flask import current_app, request
from google.oauth2.credentials import Credentials

from google_reviews_client.client import GoogleReviewsClient
from google_reviews_client.constants import BUSINESS_BASE
from google_reviews_client.models import Review


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


def get_reviews_page(client, location_name, page_token=None):
    """Fetch a single page of reviews, returning (reviews, next_page_token)."""
    url = f"{BUSINESS_BASE}/{location_name}/reviews"
    params = {}
    if page_token:
        params["pageToken"] = page_token
    data = client._authenticated_get(url, params=params)
    reviews = [Review.from_api_response(r) for r in data.get("reviews", [])]
    return reviews, data.get("nextPageToken"), data.get("totalReviewCount"), data.get("averageRating")
