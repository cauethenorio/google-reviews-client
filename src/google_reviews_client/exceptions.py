class GoogleReviewsError(Exception):
    """Base exception for all google-reviews-client errors."""

    def __init__(self, message: str = "", *, body: str = ""):
        super().__init__(message)
        self.body = body


class AuthenticationError(GoogleReviewsError):
    """Authentication failed (401)."""


class PermissionError(GoogleReviewsError):  # noqa: A001
    """Insufficient permissions (403)."""


class RateLimitError(GoogleReviewsError):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str = "", *, body: str = "", retry_after: int | None = None):
        super().__init__(message, body=body)
        self.retry_after = retry_after


class NotFoundError(GoogleReviewsError):
    """Resource not found (404)."""


class ValidationError(GoogleReviewsError):
    """Data validation error."""


class GoogleAPIError(GoogleReviewsError):
    """Google API server error (5xx)."""


class HTTPError(Exception):
    """Transport-level HTTP error (non-2xx). Not a domain exception."""

    def __init__(self, status_code: int, body: str, headers: dict | None = None):
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}
        msg = f"HTTP {status_code}"
        super().__init__(msg)
