import logging
from collections.abc import Iterator
from datetime import datetime
from http import HTTPStatus

import google.auth.credentials
import google.auth.transport
import httpx

from .constants import ACCOUNT_MGMT_BASE, BUSINESS_BASE, LOCATION_ALL_FIELDS
from .exceptions import (
    AuthenticationError,
    GoogleAPIError,
    GoogleReviewsError,
    HTTPError,
    NotFoundError,
    PermissionError,  # noqa: A004
    RateLimitError,
)
from .http_client.base_client import BaseHTTPClient
from .http_client.httpx_client import HttpxHTTPClient
from .models import Account, Location, Review

logger = logging.getLogger(__name__)


class _HttpxResponse:
    """Concrete google-auth transport response backed by httpx."""

    def __init__(self, status, headers, data):
        self.status = status
        self.headers = headers
        self.data = data


class _HttpxAuthRequest(google.auth.transport.Request):
    """Minimal google-auth transport backed by httpx (avoids requests dependency)."""

    def __call__(self, url, method="GET", body=None, headers=None, timeout=None, **_kwargs):
        response = httpx.request(method, url, content=body, headers=headers, timeout=timeout)
        return _HttpxResponse(response.status_code, response.headers, response.content)


_STATUS_TO_EXCEPTION = {
    HTTPStatus.UNAUTHORIZED: AuthenticationError,
    HTTPStatus.FORBIDDEN: PermissionError,
    HTTPStatus.NOT_FOUND: NotFoundError,
    HTTPStatus.TOO_MANY_REQUESTS: RateLimitError,
}

_STATUS_MESSAGES = {
    HTTPStatus.UNAUTHORIZED: "Authentication failed",
    HTTPStatus.FORBIDDEN: "Permission denied",
    HTTPStatus.NOT_FOUND: "Resource not found",
    HTTPStatus.TOO_MANY_REQUESTS: "Rate limit exceeded",
}


def _extract_retry_after(headers: dict) -> int | None:
    """Extract Retry-After value from response headers."""
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def _map_status_to_exception(status_code: int, body: str, headers: dict | None = None) -> GoogleReviewsError:
    """Map HTTP status codes to domain exceptions."""
    try:
        exc_class = _STATUS_TO_EXCEPTION.get(HTTPStatus(status_code))
    except ValueError:
        exc_class = None
    if exc_class is RateLimitError:
        retry_after = _extract_retry_after(headers or {})
        return RateLimitError("Rate limit exceeded", body=body, retry_after=retry_after)
    if exc_class is not None:
        message = _STATUS_MESSAGES[HTTPStatus(status_code)]
        return exc_class(message, body=body)
    if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return GoogleAPIError("Google API error", body=body)
    return GoogleReviewsError("API request failed", body=body)


class GoogleReviewsClient:
    """High-level client for Google Business Profile API."""

    http_client_class: type[BaseHTTPClient] = HttpxHTTPClient

    def __init__(self, credentials: google.auth.credentials.Credentials):
        self.credentials = credentials
        self.http_client = self.http_client_class()

    def _authenticated_get(
        self, url: str, params: dict | None = None, extra_headers: dict[str, str] | None = None
    ) -> dict:
        """Make an authenticated GET request with automatic error mapping."""
        headers: dict[str, str] = {}
        if extra_headers:
            headers.update(extra_headers)
        self.credentials.before_request(request=_HttpxAuthRequest(), method="GET", url=url, headers=headers)
        try:
            return self.http_client.get(url, params=params, headers=headers)
        except HTTPError as e:
            raise _map_status_to_exception(e.status_code, e.body, e.headers) from e

    def list_accounts(self) -> list[Account]:
        data = self._authenticated_get(f"{ACCOUNT_MGMT_BASE}/v1/accounts")
        return [Account.from_api_response(acc) for acc in data["accounts"]]

    def list_locations(self, account: str) -> list[Location]:
        data = self._authenticated_get(
            f"{ACCOUNT_MGMT_BASE}/v1/{account}/locations",
            params={"readMask": LOCATION_ALL_FIELDS},
        )
        return [Location.from_api_response(loc, account=account) for loc in data["locations"]]

    def list_reviews(
        self,
        location: str,
        *,
        since: datetime | None = None,
        order_by: str | None = None,
        language: str | None = None,
    ) -> Iterator[Review]:
        url = f"{BUSINESS_BASE}/{location}/reviews"
        page_token = None
        extra_headers = {"Accept-Language": language} if language else None

        # When syncing, order by updateTime desc so we can stop early
        # once we reach reviews we've already seen
        if since is not None and order_by is None:
            order_by = "updateTime desc"

        while True:
            params: dict[str, str] = {}
            if page_token:
                params["pageToken"] = page_token
            if order_by is not None:
                params["orderBy"] = order_by
            data = self._authenticated_get(url, params=params, extra_headers=extra_headers)
            for review_data in data["reviews"]:
                review = Review.from_api_response(review_data)
                if since is not None and review.update_time <= since:
                    return
                yield review
            page_token = data.get("nextPageToken")
            if not page_token:
                break
