"""Google Reviews Client -- a lightweight Python client for Google Business Profile reviews."""

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
from .models import (
    Account,
    BusinessHours,
    Categories,
    Category,
    LatLng,
    Location,
    LocationMetadata,
    OpenInfo,
    PhoneNumbers,
    PostalAddress,
    Profile,
    Review,
    Reviewer,
    ReviewReply,
    ReviewsPage,
    ReviewsResult,
    StarRating,
    TimePeriod,
)

__all__ = [
    "Account",
    "AuthenticationError",
    "BaseHTTPClient",
    "BusinessHours",
    "Categories",
    "Category",
    "GoogleAPIError",
    "GooglePermissionError",
    "GoogleReviewsClient",
    "GoogleReviewsError",
    "HTTPError",
    "HttpxHTTPClient",
    "LatLng",
    "Location",
    "LocationMetadata",
    "NotFoundError",
    "OpenInfo",
    "PhoneNumbers",
    "PostalAddress",
    "Profile",
    "RateLimitError",
    "Review",
    "ReviewReply",
    "Reviewer",
    "ReviewsPage",
    "ReviewsResult",
    "StarRating",
    "TimePeriod",
    "ValidationError",
    "__version__",
]
