class GoogleBusinessError(Exception):
    """Base exception for all google-business-reviews errors."""

    def __init__(self, message: str = "", *, body: str = ""):
        super().__init__(message)
        self.body = body


class AuthenticationError(GoogleBusinessError):
    """Authentication failed (401)."""


class PermissionError(GoogleBusinessError):  # noqa: A001
    """Insufficient permissions (403)."""


class RateLimitError(GoogleBusinessError):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str = "", *, body: str = "", retry_after: int | None = None):
        super().__init__(message, body=body)
        self.retry_after = retry_after


class NotFoundError(GoogleBusinessError):
    """Resource not found (404)."""


class ValidationError(GoogleBusinessError):
    """Data validation error."""


class GoogleAPIError(GoogleBusinessError):
    """Google API server error (5xx)."""


class HTTPError(Exception):
    """Transport-level HTTP error (non-2xx). Not a domain exception."""

    def __init__(self, status_code: int, body: str, headers: dict | None = None):
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}
        msg = f"HTTP {status_code}"
        super().__init__(msg)
