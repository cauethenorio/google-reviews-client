from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("google-reviews-client")
except PackageNotFoundError:
    __version__ = "dev"

from .client import GoogleReviewsClient
from .exceptions import (
    AuthenticationError,
    GoogleAPIError,
    GooglePermissionError,
    GoogleReviewsError,
    HTTPError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from .http_client import BaseHTTPClient, HttpxHTTPClient
from .models import Account, Location, Review, Reviewer, ReviewReply, StarRating

__all__ = [
    "Account",
    "AuthenticationError",
    "BaseHTTPClient",
    "GoogleAPIError",
    "GooglePermissionError",
    "GoogleReviewsClient",
    "GoogleReviewsError",
    "HTTPError",
    "HttpxHTTPClient",
    "Location",
    "NotFoundError",
    "RateLimitError",
    "Review",
    "ReviewReply",
    "Reviewer",
    "StarRating",
    "ValidationError",
    "__version__",
]
