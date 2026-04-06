from datetime import datetime, timezone

from google_reviews_client.models import (
    Account,
    Location,
    Review,
    Reviewer,
    ReviewReply,
    ReviewsPage,
    ReviewsResult,
    StarRating,
    _chain,
)


class TestAccountFromApiResponse:
    def test_complete_data(self):
        data = {
            "name": "accounts/123456789",
            "accountName": "My Business",
            "type": "PERSONAL",
            "verificationState": "VERIFIED",
            "vettedState": "VETTED",
        }
        account = Account.from_api_response(data)
        assert account.name == "accounts/123456789"
        assert account.account_name == "My Business"
        assert account.type == "PERSONAL"
        assert account.verification_state == "VERIFIED"
        assert account.vetted_state == "VETTED"

    def test_partial_data(self):
        data = {
            "name": "accounts/999",
            "accountName": "Minimal Biz",
        }
        account = Account.from_api_response(data)
        assert account.name == "accounts/999"
        assert account.account_name == "Minimal Biz"
        assert account.type is None
        assert account.verification_state is None
        assert account.vetted_state is None

    def test_empty_dict(self):
        account = Account.from_api_response({})
        assert account.name == ""
        assert account.account_name == ""
        assert account.type is None
        assert account.verification_state is None
        assert account.vetted_state is None


class TestLocationFromApiResponse:
    def test_complete_data(self):
        data = {
            "name": "locations/987654321",
            "title": "My Store - Downtown",
            "storeCode": "STORE-001",
        }
        location = Location.from_api_response(data, account="accounts/123")
        assert location.name == "locations/987654321"
        assert location.location_id == "987654321"
        assert location.account_id == "123"
        assert location.title == "My Store - Downtown"
        assert location.store_code == "STORE-001"

    def test_partial_data(self):
        data = {
            "name": "locations/555",
        }
        location = Location.from_api_response(data, account="accounts/456")
        assert location.name == "locations/555"
        assert location.location_id == "555"
        assert location.account_id == "456"
        assert location.title is None
        assert location.store_code is None

    def test_empty_dict(self):
        location = Location.from_api_response({}, account="accounts/789")
        assert location.name == ""
        assert location.location_id == ""
        assert location.account_id == "789"
        assert location.title is None
        assert location.store_code is None


class TestStarRatingFromString:
    def test_all_valid_values(self):
        assert StarRating.from_string("ONE") == StarRating.ONE
        assert StarRating.from_string("TWO") == StarRating.TWO
        assert StarRating.from_string("THREE") == StarRating.THREE
        assert StarRating.from_string("FOUR") == StarRating.FOUR
        assert StarRating.from_string("FIVE") == StarRating.FIVE

    def test_unknown_string_defaults_to_unspecified(self):
        assert StarRating.from_string("UNKNOWN") == StarRating.STAR_RATING_UNSPECIFIED
        assert StarRating.from_string("") == StarRating.STAR_RATING_UNSPECIFIED

    def test_star_rating_unspecified_from_string(self):
        assert StarRating.from_string("STAR_RATING_UNSPECIFIED") == StarRating.STAR_RATING_UNSPECIFIED

    def test_enum_values(self):
        assert StarRating.STAR_RATING_UNSPECIFIED.value == 0
        assert StarRating.ONE.value == 1
        assert StarRating.FIVE.value == 5


class TestReviewerFromApiResponse:
    def test_complete_data(self):
        data = {
            "displayName": "John Doe",
            "profilePhotoUrl": "https://lh3.googleusercontent.com/photo",
            "isAnonymous": False,
        }
        reviewer = Reviewer.from_api_response(data)
        assert reviewer.display_name == "John Doe"
        assert reviewer.profile_photo_url == "https://lh3.googleusercontent.com/photo"
        assert reviewer.is_anonymous is False

    def test_partial_data(self):
        data = {"displayName": "Jane"}
        reviewer = Reviewer.from_api_response(data)
        assert reviewer.display_name == "Jane"
        assert reviewer.profile_photo_url is None
        assert reviewer.is_anonymous is False

    def test_empty_dict_defaults(self):
        reviewer = Reviewer.from_api_response({})
        assert reviewer.display_name == "Anonymous"
        assert reviewer.profile_photo_url is None
        assert reviewer.is_anonymous is False

    def test_anonymous_reviewer(self):
        data = {"isAnonymous": True}
        reviewer = Reviewer.from_api_response(data)
        assert reviewer.display_name == "Anonymous"
        assert reviewer.is_anonymous is True


class TestReviewReplyFromApiResponse:
    def test_complete_data(self):
        data = {
            "comment": "Thank you for your feedback!",
            "updateTime": "2024-01-16T08:00:00Z",
        }
        reply = ReviewReply.from_api_response(data)
        assert reply.comment == "Thank you for your feedback!"
        assert reply.update_time == datetime(2024, 1, 16, 8, 0, 0, tzinfo=timezone.utc)

    def test_timestamp_with_offset(self):
        data = {
            "comment": "Thanks!",
            "updateTime": "2024-01-16T08:00:00+00:00",
        }
        reply = ReviewReply.from_api_response(data)
        assert reply.update_time == datetime(2024, 1, 16, 8, 0, 0, tzinfo=timezone.utc)


class TestReviewFromApiResponse:
    def _make_complete_review_data(self):
        return {
            "reviewId": "abc123",
            "name": "accounts/123/locations/456/reviews/abc123",
            "reviewer": {
                "displayName": "John Doe",
                "profilePhotoUrl": "https://lh3.googleusercontent.com/photo",
                "isAnonymous": False,
            },
            "starRating": "FIVE",
            "comment": "Great service!",
            "createTime": "2024-01-15T10:30:00Z",
            "updateTime": "2024-01-15T10:30:00Z",
            "reviewReply": {
                "comment": "Thank you for your feedback!",
                "updateTime": "2024-01-16T08:00:00Z",
            },
        }

    def test_complete_review(self):
        data = self._make_complete_review_data()
        review = Review.from_api_response(data)
        assert review.review_id == "abc123"
        assert review.name == "accounts/123/locations/456/reviews/abc123"
        assert review.star_rating == StarRating.FIVE
        assert review.comment == "Great service!"
        assert review.create_time == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert review.update_time == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_nested_reviewer(self):
        data = self._make_complete_review_data()
        review = Review.from_api_response(data)
        assert review.reviewer.display_name == "John Doe"
        assert review.reviewer.profile_photo_url == "https://lh3.googleusercontent.com/photo"
        assert review.reviewer.is_anonymous is False

    def test_nested_review_reply(self):
        data = self._make_complete_review_data()
        review = Review.from_api_response(data)
        assert review.review_reply is not None
        assert review.review_reply.comment == "Thank you for your feedback!"

    def test_review_without_reply(self):
        data = self._make_complete_review_data()
        del data["reviewReply"]
        review = Review.from_api_response(data)
        assert review.review_reply is None

    def test_partial_data(self):
        data = {
            "createTime": "2024-01-15T10:30:00Z",
            "updateTime": "2024-01-15T10:30:00Z",
        }
        review = Review.from_api_response(data)
        assert review.review_id == ""
        assert review.name is None
        assert review.comment == ""
        assert review.star_rating == StarRating.STAR_RATING_UNSPECIFIED  # missing starRating defaults to unspecified
        assert review.reviewer.display_name == "Anonymous"

    def test_rating_value_property(self):
        data = self._make_complete_review_data()
        data["starRating"] = "THREE"
        review = Review.from_api_response(data)
        assert review.rating_value == 3

    def test_has_reply_property(self):
        data = self._make_complete_review_data()
        review = Review.from_api_response(data)
        assert review.has_reply is True

        del data["reviewReply"]
        review_no_reply = Review.from_api_response(data)
        assert review_no_reply.has_reply is False

    def test_to_dict(self):
        data = self._make_complete_review_data()
        review = Review.from_api_response(data)
        result = review.to_dict()
        assert result["review_id"] == "abc123"
        assert result["rating"] == 5
        assert result["comment"] == "Great service!"
        assert result["reviewer"]["display_name"] == "John Doe"
        assert result["review_reply"]["comment"] == "Thank you for your feedback!"

    def test_to_dict_without_reply(self):
        data = self._make_complete_review_data()
        del data["reviewReply"]
        review = Review.from_api_response(data)
        result = review.to_dict()
        assert result["review_reply"] is None


class TestReviewsPage:
    def test_creation_with_defaults(self):
        page = ReviewsPage(reviews=[])
        assert page.reviews == []
        assert page.next_page_token is None
        assert page.total_review_count is None
        assert page.average_rating is None

    def test_creation_with_all_fields(self):
        review = Review.from_api_response({
            "reviewId": "r1",
            "reviewer": {"displayName": "Test"},
            "starRating": "FIVE",
            "comment": "Good",
            "createTime": "2024-01-01T00:00:00Z",
            "updateTime": "2024-01-01T00:00:00Z",
        })
        page = ReviewsPage(
            reviews=[review],
            next_page_token="tok123",  # noqa: S106
            total_review_count=42,
            average_rating=4.5,
        )
        assert len(page.reviews) == 1
        assert page.reviews[0].review_id == "r1"
        assert page.next_page_token == "tok123"
        assert page.total_review_count == 42
        assert page.average_rating == 4.5


def _make_review(rid):
    """Helper to create a Review with minimal data."""
    return Review.from_api_response({
        "reviewId": rid,
        "reviewer": {"displayName": "User"},
        "starRating": "FIVE",
        "comment": "Good",
        "createTime": "2024-01-01T00:00:00Z",
        "updateTime": "2024-01-01T00:00:00Z",
    })


class TestChain:
    def test_chain_concatenates_first_and_rest(self):
        assert list(_chain([1, 2], iter([3, 4]))) == [1, 2, 3, 4]

    def test_chain_empty_first(self):
        assert list(_chain([], iter([1, 2]))) == [1, 2]

    def test_chain_empty_rest(self):
        assert list(_chain([1, 2], iter([]))) == [1, 2]


class TestReviewsResult:
    def test_metadata_available_immediately(self):
        result = ReviewsResult(
            first_page_reviews=[],
            remaining=iter([]),
            total_review_count=42,
            average_rating=4.5,
        )
        assert result.total_review_count == 42
        assert result.average_rating == 4.5

    def test_reviews_is_generator(self):
        r1 = _make_review("r1")
        result = ReviewsResult(
            first_page_reviews=[r1],
            remaining=iter([]),
            total_review_count=1,
            average_rating=5.0,
        )
        assert hasattr(result.reviews, "__next__")

    def test_iter_yields_reviews(self):
        r1 = _make_review("r1")
        r2 = _make_review("r2")
        r3 = _make_review("r3")
        result = ReviewsResult(
            first_page_reviews=[r1, r2],
            remaining=iter([r3]),
            total_review_count=3,
            average_rating=5.0,
        )
        reviews = list(result)
        assert len(reviews) == 3
        assert [r.review_id for r in reviews] == ["r1", "r2", "r3"]

    def test_single_use_generator(self):
        r1 = _make_review("r1")
        result = ReviewsResult(
            first_page_reviews=[r1],
            remaining=iter([]),
            total_review_count=1,
            average_rating=5.0,
        )
        assert len(list(result)) == 1
        assert len(list(result)) == 0

    def test_reviews_property_returns_same_generator(self):
        result = ReviewsResult(
            first_page_reviews=[],
            remaining=iter([]),
            total_review_count=0,
            average_rating=0.0,
        )
        assert result.reviews is result.reviews
