from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("google-reviews-client")
except PackageNotFoundError:
    __version__ = "dev"

from .client import GoogleReviewsClient
from .exceptions import (
    AuthenticationError,
    GoogleAPIError,
    GoogleReviewsError,
    HTTPError,
    NotFoundError,
    PermissionError,  # noqa: A004
    RateLimitError,
    ValidationError,
)
from .http_client import BaseHTTPClient, HttpxHTTPClient
from .models import Account, Location, Review, Reviewer, ReviewReply, StarRating

__all__ = [
    "__version__",
    "Account",
    "AuthenticationError",
    "BaseHTTPClient",
    "GoogleAPIError",
    "GoogleReviewsClient",
    "GoogleReviewsError",
    "HTTPError",
    "HttpxHTTPClient",
    "Location",
    "NotFoundError",
    "PermissionError",
    "RateLimitError",
    "Review",
    "ReviewReply",
    "Reviewer",
    "StarRating",
    "ValidationError",
]
