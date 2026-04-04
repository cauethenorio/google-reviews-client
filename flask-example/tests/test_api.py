"""Tests for api.py helpers: get_client() and get_reviews_page()."""

from unittest import mock
from unittest.mock import MagicMock

SAMPLE_REVIEW_API = {
    "reviewId": "r1",
    "reviewer": {"displayName": "Alice"},
    "starRating": "FIVE",
    "comment": "Great!",
    "createTime": "2025-03-15T10:00:00Z",
    "updateTime": "2025-03-15T10:00:00Z",
}


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
        mock_client._authenticated_get.return_value = {
            "reviews": [SAMPLE_REVIEW_API],
            "nextPageToken": "tok2",
        }

        from api import get_reviews_page

        reviews, next_token = get_reviews_page(mock_client, "accounts/1/locations/2")
        assert len(reviews) == 1
        assert reviews[0].review_id == "r1"
        assert next_token == "tok2"

    def test_returns_reviews_without_next_token(self):
        """No nextPageToken returns None for token."""
        mock_client = MagicMock()
        mock_client._authenticated_get.return_value = {
            "reviews": [SAMPLE_REVIEW_API],
        }

        from api import get_reviews_page

        reviews, next_token = get_reviews_page(mock_client, "accounts/1/locations/2")
        assert len(reviews) == 1
        assert next_token is None

    def test_returns_empty_list_when_no_reviews(self):
        """Empty response returns empty list and None."""
        mock_client = MagicMock()
        mock_client._authenticated_get.return_value = {}

        from api import get_reviews_page

        reviews, next_token = get_reviews_page(mock_client, "accounts/1/locations/2")
        assert reviews == []
        assert next_token is None

    def test_passes_page_token_to_api(self):
        """page_token is forwarded as pageToken param."""
        mock_client = MagicMock()
        mock_client._authenticated_get.return_value = {}

        from api import get_reviews_page

        get_reviews_page(mock_client, "accounts/1/locations/2", page_token="tok1")
        call_args = mock_client._authenticated_get.call_args
        assert call_args[1]["params"]["pageToken"] == "tok1"
