"""Data models for Google Business Profile API responses."""

from collections.abc import Generator, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


def _parse_timestamp(timestamp_str: str) -> datetime:
    """Convert RFC3339 timestamp to datetime."""
    if timestamp_str.endswith("Z"):
        timestamp_str = timestamp_str[:-1] + "+00:00"
    return datetime.fromisoformat(timestamp_str)


class StarRating(Enum):
    """Enum for review ratings."""

    STAR_RATING_UNSPECIFIED = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5

    @classmethod
    def from_string(cls, rating_str: str) -> "StarRating":
        """Convert API string to enum."""
        try:
            return cls[rating_str]
        except KeyError:
            return cls.STAR_RATING_UNSPECIFIED


@dataclass
class Reviewer:
    """Review author data."""

    display_name: str
    profile_photo_url: str | None = None
    is_anonymous: bool = False

    @classmethod
    def from_api_response(cls, data: dict) -> "Reviewer":
        """Create Reviewer from API response."""
        return cls(
            display_name=data.get("displayName", "Anonymous"),
            profile_photo_url=data.get("profilePhotoUrl"),
            is_anonymous=data.get("isAnonymous", False),
        )


@dataclass
class ReviewReply:
    """Business reply to a review."""

    comment: str
    update_time: datetime

    @classmethod
    def from_api_response(cls, data: dict) -> "ReviewReply":
        """Create ReviewReply from API response."""
        return cls(comment=data["comment"], update_time=_parse_timestamp(data["updateTime"]))


@dataclass
class Review:
    """Data model for a Google Business review."""

    review_id: str
    reviewer: Reviewer
    star_rating: StarRating
    comment: str
    create_time: datetime
    update_time: datetime
    review_reply: ReviewReply | None = None

    name: str | None = None  # Full resource name

    @property
    def rating_value(self) -> int:
        """Return the numeric rating value (1-5)."""
        return self.star_rating.value

    @property
    def has_reply(self) -> bool:
        """Check if the review has a reply."""
        return self.review_reply is not None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "review_id": self.review_id,
            "name": self.name,
            "reviewer": {
                "display_name": self.reviewer.display_name,
                "profile_photo_url": self.reviewer.profile_photo_url,
                "is_anonymous": self.reviewer.is_anonymous,
            },
            "rating": self.rating_value,
            "comment": self.comment,
            "create_time": self.create_time.isoformat(),
            "update_time": self.update_time.isoformat(),
            "review_reply": {
                "comment": self.review_reply.comment,
                "update_time": self.review_reply.update_time.isoformat(),
            }
            if self.review_reply
            else None,
        }

    @classmethod
    def from_api_response(cls, data: dict) -> "Review":
        """Create Review from API response."""
        reviewer = Reviewer.from_api_response(data.get("reviewer", {}))

        star_rating = StarRating.from_string(data.get("starRating", "STAR_RATING_UNSPECIFIED"))

        review_reply = None
        if "reviewReply" in data:
            review_reply = ReviewReply.from_api_response(data["reviewReply"])

        return cls(
            review_id=data.get("reviewId", ""),
            name=data.get("name"),
            reviewer=reviewer,
            star_rating=star_rating,
            comment=data.get("comment", ""),
            create_time=_parse_timestamp(data["createTime"]),
            update_time=_parse_timestamp(data["updateTime"]),
            review_reply=review_reply,
        )


@dataclass
class ReviewsPage:
    """A single page of reviews with pagination and aggregate metadata."""

    reviews: list[Review]
    next_page_token: str | None = None
    total_review_count: int | None = None
    average_rating: float | None = None


def _chain(first: list, rest: Iterator) -> Generator:
    """Yield all items from first, then all items from rest."""
    yield from first
    yield from rest


class ReviewsResult:
    """Result of list_reviews() -- eager first page with lazy remaining pages.

    Metadata (total_review_count, average_rating) is available immediately
    after construction. Reviews are accessed via iteration or .reviews property,
    yielding first-page reviews from memory then lazily fetching subsequent pages.
    """

    def __init__(
        self,
        *,
        first_page_reviews: list[Review],
        remaining: Iterator[Review],
        total_review_count: int | None,
        average_rating: float | None,
    ):
        """Initialize with first page reviews, remaining generator, and metadata."""
        self.total_review_count = total_review_count
        self.average_rating = average_rating
        self._reviews = _chain(first_page_reviews, remaining)

    @property
    def reviews(self) -> Generator:
        """Single-use generator: first page from memory, then lazy remaining pages."""
        return self._reviews

    def __iter__(self):
        """Iterate over all reviews (first page + remaining)."""
        return self._reviews

    def __next__(self):
        """Return next review from the generator."""
        return next(self._reviews)


@dataclass
class PostalAddress:
    """Postal address for a location's storefront."""

    address_lines: list[str] = field(default_factory=list)
    region_code: str | None = None
    language_code: str | None = None
    postal_code: str | None = None
    administrative_area: str | None = None
    locality: str | None = None
    sublocality: str | None = None

    @property
    def formatted(self) -> str:
        """Join address components into a readable string."""
        parts = list(self.address_lines)
        if self.locality:
            parts.append(self.locality)
        if self.administrative_area:
            parts.append(self.administrative_area)
        if self.postal_code:
            parts.append(self.postal_code)
        return ", ".join(parts)

    @classmethod
    def from_api_response(cls, data: dict) -> "PostalAddress":
        """Create PostalAddress from API response."""
        return cls(
            address_lines=data.get("addressLines", []),
            region_code=data.get("regionCode"),
            language_code=data.get("languageCode"),
            postal_code=data.get("postalCode"),
            administrative_area=data.get("administrativeArea"),
            locality=data.get("locality"),
            sublocality=data.get("sublocality"),
        )


@dataclass
class PhoneNumbers:
    """Phone numbers for a location."""

    primary_phone: str
    additional_phones: list[str] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "PhoneNumbers":
        """Create PhoneNumbers from API response."""
        return cls(
            primary_phone=data["primaryPhone"],
            additional_phones=data.get("additionalPhones", []),
        )


@dataclass
class Category:
    """A single business category."""

    name: str
    display_name: str | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Category":
        """Create Category from API response."""
        return cls(
            name=data["name"],
            display_name=data.get("displayName"),
        )


@dataclass
class Categories:
    """Categories for a location."""

    primary_category: Category
    additional_categories: list[Category] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "Categories":
        """Create Categories from API response."""
        return cls(
            primary_category=Category.from_api_response(data["primaryCategory"]),
            additional_categories=[Category.from_api_response(c) for c in data.get("additionalCategories", [])],
        )


@dataclass
class LatLng:
    """Geographic coordinates."""

    latitude: float
    longitude: float

    @classmethod
    def from_api_response(cls, data: dict) -> "LatLng":
        """Create LatLng from API response."""
        return cls(
            latitude=data["latitude"],
            longitude=data["longitude"],
        )


@dataclass
class OpenInfo:
    """Opening status of a location."""

    status: str
    can_reopen: bool | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> "OpenInfo":
        """Create OpenInfo from API response."""
        return cls(
            status=data["status"],
            can_reopen=data.get("canReopen"),
        )


@dataclass
class LocationMetadata:
    """Read-only metadata for a location."""

    place_id: str | None = None
    maps_uri: str | None = None
    new_review_uri: str | None = None
    has_pending_edits: bool | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> "LocationMetadata":
        """Create LocationMetadata from API response."""
        return cls(
            place_id=data.get("placeId"),
            maps_uri=data.get("mapsUri"),
            new_review_uri=data.get("newReviewUri"),
            has_pending_edits=data.get("hasPendingEdits"),
        )


@dataclass
class Profile:
    """Business profile description."""

    description: str

    @classmethod
    def from_api_response(cls, data: dict) -> "Profile":
        """Create Profile from API response."""
        return cls(description=data["description"])


@dataclass
class TimePeriod:
    """A period of time that a location is open."""

    open_day: str
    open_time: str
    close_day: str
    close_time: str

    @classmethod
    def from_api_response(cls, data: dict) -> "TimePeriod":
        """Create TimePeriod from API response."""
        open_time_dict = data.get("openTime", {})
        close_time_dict = data.get("closeTime", {})
        return cls(
            open_day=data["openDay"],
            open_time=f"{open_time_dict.get('hours', 0):02d}:{open_time_dict.get('minutes', 0):02d}",
            close_day=data["closeDay"],
            close_time=f"{close_time_dict.get('hours', 0):02d}:{close_time_dict.get('minutes', 0):02d}",
        )


@dataclass
class BusinessHours:
    """Regular business hours for a location."""

    periods: list[TimePeriod]

    @classmethod
    def from_api_response(cls, data: dict) -> "BusinessHours":
        """Create BusinessHours from API response."""
        return cls(
            periods=[TimePeriod.from_api_response(p) for p in data["periods"]],
        )


@dataclass
class Location:
    """Google Business location.

    See: https://developers.google.com/my-business/reference/businessinformation/rest/v1/accounts.locations

    """

    name: str
    location_id: str
    account_id: str
    title: str | None = None
    store_code: str | None = None
    language_code: str | None = None
    phone_numbers: PhoneNumbers | None = None
    categories: Categories | None = None
    address: PostalAddress | None = None
    website_uri: str | None = None
    regular_hours: BusinessHours | None = None
    latlng: LatLng | None = None
    open_info: OpenInfo | None = None
    metadata: LocationMetadata | None = None
    profile: Profile | None = None
    labels: list[str] | None = None

    @property
    def full_name(self) -> str:
        """Return the full name in API format."""
        return f"accounts/{self.account_id}/locations/{self.location_id}"

    @classmethod
    def from_api_response(cls, data: dict, *, account: str) -> "Location":
        """Create Location from Google API response.

        Args:
            data: API response dict for a single location.
            account: Account resource name (e.g., "accounts/123").

        """
        name = data.get("name", "")
        # Extract location_id from resource name (e.g., "locations/987" -> "987")
        location_id = name.split("/")[-1] if "/" in name else ""
        # Extract account_id from account resource name (e.g., "accounts/123" -> "123")
        account_id = account.split("/")[-1] if "/" in account else account
        return cls(
            name=name,
            location_id=location_id,
            account_id=account_id,
            title=data.get("title"),
            store_code=data.get("storeCode"),
            language_code=data.get("languageCode"),
            phone_numbers=PhoneNumbers.from_api_response(data["phoneNumbers"]) if "phoneNumbers" in data else None,
            categories=Categories.from_api_response(data["categories"]) if "categories" in data else None,
            address=PostalAddress.from_api_response(data["storefrontAddress"]) if "storefrontAddress" in data else None,
            website_uri=data.get("websiteUri"),
            regular_hours=BusinessHours.from_api_response(data["regularHours"]) if "regularHours" in data else None,
            latlng=LatLng.from_api_response(data["latlng"]) if "latlng" in data else None,
            open_info=OpenInfo.from_api_response(data["openInfo"]) if "openInfo" in data else None,
            metadata=LocationMetadata.from_api_response(data["metadata"]) if "metadata" in data else None,
            profile=Profile.from_api_response(data["profile"]) if "profile" in data else None,
            labels=data.get("labels"),
        )


@dataclass
class Account:
    """Google Business Profile account.

    An account is a container for your location. If you are the only user
    who manages locations for your business, you can use your personal
    Google Account.

    See: https://developers.google.com/my-business/reference/accountmanagement/rest/v1/accounts#resource:-account

    """

    name: str
    account_name: str
    type: str | None = None
    verification_state: str | None = None
    vetted_state: str | None = None
    role: str | None = None
    account_number: str | None = None
    permission_level: str | None = None
    organization_info: dict | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Account":
        """Create Account from Google API response."""
        return cls(
            name=data.get("name", ""),
            account_name=data.get("accountName", ""),
            type=data.get("type"),
            verification_state=data.get("verificationState"),
            vetted_state=data.get("vettedState"),
            role=data.get("role"),
            account_number=data.get("accountNumber"),
            permission_level=data.get("permissionLevel"),
            organization_info=data.get("organizationInfo"),
        )
