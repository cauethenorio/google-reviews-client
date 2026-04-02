from dataclasses import dataclass
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
class Location:
    """https://developers.google.com/my-business/reference/businessinformation/rest/v1/accounts.locations

    Google Business location.
    """

    name: str
    location_id: str
    account_id: str
    title: str | None = None
    store_code: str | None = None
    language_code: str | None = None

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
        )


@dataclass
class Account:
    """https://developers.google.com/my-business/reference/accountmanagement/rest/v1/accounts#resource:-account

    An account is a container for your location. If you are the only user who manages locations for your business,
    you can use your personal Google Account.
    """

    name: str
    account_name: str
    type: str | None = None
    verification_state: str | None = None
    vetted_state: str | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Account":
        """Create Account from Google API response."""
        return cls(
            name=data.get("name", ""),
            account_name=data.get("accountName", ""),
            type=data.get("type"),
            verification_state=data.get("verificationState"),
            vetted_state=data.get("vettedState"),
        )
