"""HTTP transport implementation using httpx with retry logic."""

import logging
import time

import httpx

from google_reviews_client.exceptions import HTTPError

from .base_client import BaseHTTPClient

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE = 1.0


def _parse_retry_after(headers: httpx.Headers) -> float | None:
    raw = headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


class HttpxHTTPClient(BaseHTTPClient):
    """Default HTTP transport using httpx."""

    def __init__(self, *, max_retries: int = _DEFAULT_MAX_RETRIES, backoff_base: float = _DEFAULT_BACKOFF_BASE):
        """Initialize the httpx client with retry settings.

        Args:
            max_retries: Maximum number of retry attempts for retryable status codes.
            backoff_base: Base delay in seconds for exponential backoff.

        """
        self._client = httpx.Client(timeout=30)
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self):
        """Enter the context manager."""
        return self

    def __exit__(self, *_args):
        """Exit the context manager and close connections."""
        self.close()

    def get(self, url: str, *, params: dict | None = None, headers: dict | None = None) -> dict:
        """Make a GET request with automatic retries on transient errors.

        Args:
            url: Request URL.
            params: Optional query parameters.
            headers: Optional request headers.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            HTTPError: If the request fails after all retry attempts.

        """
        logger.debug("GET %s params=%s", url, params)
        last_response: httpx.Response | None = None

        for attempt in range(1 + self._max_retries):
            response = self._client.get(url, params=params, headers=headers)
            logger.debug("Response: %d (%d bytes)", response.status_code, len(response.content))

            if response.is_success:
                return response.json()

            if response.status_code not in _RETRYABLE_STATUS_CODES or attempt == self._max_retries:
                raise HTTPError(response.status_code, response.text, headers=dict(response.headers))

            last_response = response
            retry_after = _parse_retry_after(response.headers)
            delay = retry_after if retry_after is not None else self._backoff_base * (2**attempt)
            logger.warning(
                "Retryable %d response, attempt %d/%d, retrying in %.1fs",
                response.status_code,
                attempt + 1,
                self._max_retries,
                delay,
            )
            time.sleep(delay)

        # Should not be reached, but just in case
        raise HTTPError(last_response.status_code, last_response.text, headers=dict(last_response.headers))  # type: ignore[union-attr]
