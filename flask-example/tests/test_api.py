"""Tests for api.py helpers: get_client(), get_reviews_page(), and get_all_reviews()."""

from unittest import mock
from unittest.mock import MagicMock

from google_reviews_client.models import Review, ReviewsPage

SAMPLE_REVIEW_API = {
    "reviewId": "r1",
    "reviewer": {"displayName": "Alice"},
    "starRating": "FIVE",
    "comment": "Great!",
    "createTime": "2025-03-15T10:00:00Z",
    "updateTime": "2025-03-15T10:00:00Z",
}


def _sample_review(review_id="r1"):
    return Review.from_api_response({**SAMPLE_REVIEW_API, "reviewId": review_id})


class TestGetClient:
    """Test get_client() credential reconstruction."""

    def test_get_client_returns_client_with_valid_cookie(self, app, authenticated_cookie):
        """Valid auth cookie produces a GoogleReviewsClient instance."""
        from cookies import TOKEN_COOKIE_NAME

        with app.test_request_context("/", headers={"Cookie": f"{TOKEN_COOKIE_NAME}={authenticated_cookie}"}):
            from api import get_client

            client = get_client()
            assert client is not None

    def test_get_client_returns_none_without_cookie(self, app):
        """No cookie returns None."""
        with app.test_request_context("/"):
            from api import get_client

            assert get_client() is None

    @mock.patch("api.decrypt_tokens", return_value=None)
    def test_get_client_returns_none_with_invalid_cookie(self, mock_decrypt, app):
        """Invalid cookie (decrypt returns None) returns None."""
        from cookies import TOKEN_COOKIE_NAME

        with app.test_request_context("/", headers={"Cookie": f"{TOKEN_COOKIE_NAME}=bad-cookie"}):
            from api import get_client

            assert get_client() is None


class TestGetReviewsPage:
    """Test get_reviews_page() review fetching."""

    def test_returns_reviews_and_next_token(self):
        """Returns parsed reviews and next page token."""
        mock_client = MagicMock()
        mock_client.get_reviews_page.return_value = ReviewsPage(
            reviews=[_sample_review()],
            next_page_token="tok2",
        )

        from api import get_reviews_page

        reviews, next_token, total_count, avg_rating = get_reviews_page(mock_client, "accounts/1/locations/2")
        assert len(reviews) == 1
        assert reviews[0].review_id == "r1"
        assert next_token == "tok2"
        assert total_count is None
        assert avg_rating is None

    def test_returns_reviews_without_next_token(self):
        """No next_page_token returns None for token."""
        mock_client = MagicMock()
        mock_client.get_reviews_page.return_value = ReviewsPage(reviews=[_sample_review()])

        from api import get_reviews_page

        reviews, next_token, total_count, avg_rating = get_reviews_page(mock_client, "accounts/1/locations/2")
        assert len(reviews) == 1
        assert next_token is None
        assert total_count is None
        assert avg_rating is None

    def test_returns_empty_list_when_no_reviews(self):
        """Empty page returns empty list and None."""
        mock_client = MagicMock()
        mock_client.get_reviews_page.return_value = ReviewsPage(reviews=[])

        from api import get_reviews_page

        reviews, next_token, total_count, avg_rating = get_reviews_page(mock_client, "accounts/1/locations/2")
        assert reviews == []
        assert next_token is None
        assert total_count is None
        assert avg_rating is None

    def test_forwards_args_to_client(self):
        """page_token, page_size, and language are forwarded to the client."""
        mock_client = MagicMock()
        mock_client.get_reviews_page.return_value = ReviewsPage(reviews=[])

        from api import get_reviews_page

        get_reviews_page(mock_client, "accounts/1/locations/2", page_token="tok1")
        mock_client.get_reviews_page.assert_called_once_with(
            "accounts/1/locations/2", page_token="tok1", page_size=50, language=None
        )

    def test_strips_language_whitespace(self):
        """language is stripped before being forwarded."""
        mock_client = MagicMock()
        mock_client.get_reviews_page.return_value = ReviewsPage(reviews=[])

        from api import get_reviews_page

        get_reviews_page(mock_client, "accounts/1/locations/2", language=" pt-BR ")
        call_kwargs = mock_client.get_reviews_page.call_args.kwargs
        assert call_kwargs["language"] == "pt-BR"

    def test_returns_summary_data_when_present(self):
        """Returns total_review_count and average_rating from the page."""
        mock_client = MagicMock()
        mock_client.get_reviews_page.return_value = ReviewsPage(
            reviews=[_sample_review()],
            next_page_token="token123",
            total_review_count=42,
            average_rating=4.3,
        )

        from api import get_reviews_page

        reviews, next_token, total_count, avg_rating = get_reviews_page(mock_client, "accounts/1/locations/2")
        assert len(reviews) == 1
        assert next_token == "token123"
        assert total_count == 42
        assert avg_rating == 4.3

    def test_returns_none_when_summary_data_missing(self):
        """Missing total_review_count/average_rating return as None."""
        mock_client = MagicMock()
        mock_client.get_reviews_page.return_value = ReviewsPage(reviews=[_sample_review()])

        from api import get_reviews_page

        reviews, next_token, total_count, avg_rating = get_reviews_page(mock_client, "accounts/1/locations/2")
        assert len(reviews) == 1
        assert next_token is None
        assert total_count is None
        assert avg_rating is None


class TestGetAllReviews:
    """Test get_all_reviews() pagination loop."""

    def test_accumulates_reviews_across_pages(self):
        """Follows next_page_token until exhausted, preserving order."""
        mock_client = MagicMock()
        mock_client.get_reviews_page.side_effect = [
            ReviewsPage(reviews=[_sample_review("r1")], next_page_token="tok2"),
            ReviewsPage(reviews=[_sample_review("r2")], next_page_token=None),
        ]

        from api import get_all_reviews

        all_reviews = get_all_reviews(mock_client, "accounts/1/locations/2")
        assert [r.review_id for r in all_reviews] == ["r1", "r2"]
        assert mock_client.get_reviews_page.call_count == 2
        second_call_kwargs = mock_client.get_reviews_page.call_args_list[1].kwargs
        assert second_call_kwargs["page_token"] == "tok2"

    def test_single_page_makes_one_call(self):
        """No next_page_token stops after the first request."""
        mock_client = MagicMock()
        mock_client.get_reviews_page.return_value = ReviewsPage(reviews=[_sample_review()])

        from api import get_all_reviews

        all_reviews = get_all_reviews(mock_client, "accounts/1/locations/2")
        assert len(all_reviews) == 1
        mock_client.get_reviews_page.assert_called_once()

    def test_empty_location_returns_empty_list(self):
        """A location with no reviews returns an empty list."""
        mock_client = MagicMock()
        mock_client.get_reviews_page.return_value = ReviewsPage(reviews=[])

        from api import get_all_reviews

        assert get_all_reviews(mock_client, "accounts/1/locations/2") == []
