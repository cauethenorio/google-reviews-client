from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import google.auth.credentials
import httpx

from google_reviews_client.client import GoogleReviewsClient, _HttpxAuthRequest, _HttpxResponse
from google_reviews_client.exceptions import (
    AuthenticationError,
    GoogleAPIError,
    GooglePermissionError,
    GoogleReviewsError,
    HTTPError,
    NotFoundError,
    RateLimitError,
)
from google_reviews_client.http_client import BaseHTTPClient
from google_reviews_client.models import Review


class TestGoogleReviewsClientInit:
    def test_accepts_credentials(self):
        creds = Mock(spec=google.auth.credentials.Credentials)
        client = GoogleReviewsClient(credentials=creds)
        assert client.credentials is creds

    def test_creates_http_client_from_class_attribute(self):
        creds = Mock(spec=google.auth.credentials.Credentials)
        client = GoogleReviewsClient(credentials=creds)
        assert client.http_client is not None

    def test_custom_http_client_class(self):
        class FakeHTTPClient(BaseHTTPClient):
            def get(self, _url, *, _params=None, _headers=None):
                return {}

        class CustomClient(GoogleReviewsClient):
            http_client_class = FakeHTTPClient

        creds = Mock(spec=google.auth.credentials.Credentials)
        client = CustomClient(credentials=creds)
        assert isinstance(client.http_client, FakeHTTPClient)


class TestAuthenticatedGet:
    def _make_client(self):
        creds = Mock(spec=google.auth.credentials.Credentials)
        client = GoogleReviewsClient(credentials=creds)
        client.http_client = Mock(spec=BaseHTTPClient)
        return client, creds

    def test_calls_before_request(self):
        client, creds = self._make_client()
        client.http_client.get.return_value = {"data": "ok"}

        client._authenticated_get("https://example.com/api")

        creds.before_request.assert_called_once()

    def test_passes_headers_to_http_client(self):
        client, _creds = self._make_client()
        client.http_client.get.return_value = {"data": "ok"}

        client._authenticated_get("https://example.com/api", params={"key": "val"})

        client.http_client.get.assert_called_once()
        call_kwargs = client.http_client.get.call_args
        assert call_kwargs.kwargs.get("params") == {"key": "val"}
        assert "headers" in call_kwargs.kwargs

    def test_returns_dict_on_success(self):
        client, _ = self._make_client()
        expected = {"accounts": [{"name": "acc1"}]}
        client.http_client.get.return_value = expected

        result = client._authenticated_get("https://example.com/api")

        assert result == expected

    def test_maps_401_to_authentication_error(self):
        client, _ = self._make_client()
        client.http_client.get.side_effect = HTTPError(401, '{"error": "unauthorized"}')

        try:
            client._authenticated_get("https://example.com/api")
            msg = "Expected AuthenticationError"
            raise AssertionError(msg)
        except AuthenticationError as e:
            assert e.body == '{"error": "unauthorized"}'

    def test_maps_403_to_permission_error(self):
        client, _ = self._make_client()
        client.http_client.get.side_effect = HTTPError(403, '{"error": "forbidden"}')

        try:
            client._authenticated_get("https://example.com/api")
            msg = "Expected GooglePermissionError"
            raise AssertionError(msg)
        except GooglePermissionError as e:
            assert e.body == '{"error": "forbidden"}'

    def test_maps_404_to_not_found_error(self):
        client, _ = self._make_client()
        client.http_client.get.side_effect = HTTPError(404, '{"error": "not found"}')

        try:
            client._authenticated_get("https://example.com/api")
            msg = "Expected NotFoundError"
            raise AssertionError(msg)
        except NotFoundError as e:
            assert e.body == '{"error": "not found"}'

    def test_maps_429_to_rate_limit_error(self):
        client, _ = self._make_client()
        client.http_client.get.side_effect = HTTPError(429, '{"error": "rate limit"}')

        try:
            client._authenticated_get("https://example.com/api")
            msg = "Expected RateLimitError"
            raise AssertionError(msg)
        except RateLimitError as e:
            assert e.body == '{"error": "rate limit"}'
            assert e.retry_after is None

    def test_maps_429_extracts_retry_after_from_headers(self):
        client, _ = self._make_client()
        client.http_client.get.side_effect = HTTPError(429, '{"error": "rate limit"}', headers={"Retry-After": "30"})

        try:
            client._authenticated_get("https://example.com/api")
            msg = "Expected RateLimitError"
            raise AssertionError(msg)
        except RateLimitError as e:
            assert e.retry_after == 30
            assert e.body == '{"error": "rate limit"}'

    def test_maps_429_ignores_non_numeric_retry_after(self):
        client, _ = self._make_client()
        client.http_client.get.side_effect = HTTPError(
            429, '{"error": "rate limit"}', headers={"Retry-After": "not-a-number"}
        )

        try:
            client._authenticated_get("https://example.com/api")
            msg = "Expected RateLimitError"
            raise AssertionError(msg)
        except RateLimitError as e:
            assert e.retry_after is None

    def test_maps_500_to_google_api_error(self):
        client, _ = self._make_client()
        client.http_client.get.side_effect = HTTPError(500, "Internal Server Error")

        try:
            client._authenticated_get("https://example.com/api")
            msg = "Expected GoogleAPIError"
            raise AssertionError(msg)
        except GoogleAPIError as e:
            assert e.body == "Internal Server Error"

    def test_maps_503_to_google_api_error(self):
        client, _ = self._make_client()
        client.http_client.get.side_effect = HTTPError(503, "Service Unavailable")

        try:
            client._authenticated_get("https://example.com/api")
            msg = "Expected GoogleAPIError"
            raise AssertionError(msg)
        except GoogleAPIError as e:
            assert e.body == "Service Unavailable"

    def test_maps_unknown_status_to_google_reviews_error(self):
        client, _ = self._make_client()
        client.http_client.get.side_effect = HTTPError(418, "I'm a teapot")

        try:
            client._authenticated_get("https://example.com/api")
            msg = "Expected GoogleReviewsError"
            raise AssertionError(msg)
        except GoogleReviewsError as e:
            assert e.body == "I'm a teapot"


class TestListAccounts:
    def test_list_accounts_returns_account_list(self):
        creds = Mock(spec=google.auth.credentials.Credentials)
        client = GoogleReviewsClient(credentials=creds)
        client.http_client = Mock(spec=BaseHTTPClient)
        client.http_client.get.return_value = {
            "accounts": [
                {
                    "name": "accounts/123",
                    "accountName": "Test Business",
                    "type": "PERSONAL",
                    "verificationState": "VERIFIED",
                    "vettedState": "VETTED",
                }
            ]
        }

        accounts = client.list_accounts()

        assert len(accounts) == 1
        assert accounts[0].account_name == "Test Business"

    def test_list_accounts_empty(self):
        creds = Mock(spec=google.auth.credentials.Credentials)
        client = GoogleReviewsClient(credentials=creds)
        client.http_client = Mock(spec=BaseHTTPClient)
        client.http_client.get.return_value = {}

        accounts = client.list_accounts()

        assert accounts == []


class TestListLocations:
    def _make_client(self):
        creds = Mock(spec=google.auth.credentials.Credentials)
        client = GoogleReviewsClient(credentials=creds)
        client.http_client = Mock(spec=BaseHTTPClient)
        return client

    def test_list_locations_returns_location_list(self):
        client = self._make_client()
        client.http_client.get.return_value = {
            "locations": [
                {
                    "name": "locations/987654321",
                    "title": "My Store - Downtown",
                    "storeCode": "STORE-001",
                }
            ]
        }

        locations = client.list_locations("accounts/123")

        assert len(locations) == 1
        assert locations[0].name == "locations/987654321"
        assert locations[0].location_id == "987654321"
        assert locations[0].account_id == "123"
        assert locations[0].title == "My Store - Downtown"
        assert locations[0].store_code == "STORE-001"

    def test_list_locations_empty(self):
        client = self._make_client()
        client.http_client.get.return_value = {}

        locations = client.list_locations("accounts/123")

        assert locations == []

    def test_list_locations_calls_correct_url(self):
        client = self._make_client()
        client.http_client.get.return_value = {"locations": []}

        client.list_locations("accounts/456")

        call_args = client.http_client.get.call_args
        url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        assert "accounts/456/locations" in url


class TestListReviews:
    def _make_client(self):
        creds = Mock(spec=google.auth.credentials.Credentials)
        client = GoogleReviewsClient(credentials=creds)
        client.http_client = Mock(spec=BaseHTTPClient)
        return client

    def _review_data(self, review_id="r1", rating="FIVE", comment="Great!", update_time="2024-01-15T10:00:00Z"):
        return {
            "reviewId": review_id,
            "reviewer": {"displayName": "User"},
            "starRating": rating,
            "comment": comment,
            "createTime": "2024-01-01T00:00:00Z",
            "updateTime": update_time,
        }

    def test_single_page_yields_reviews(self):
        client = self._make_client()
        client.http_client.get.return_value = {
            "reviews": [self._review_data("r1"), self._review_data("r2")],
        }

        reviews = list(client.list_reviews("accounts/1/locations/2"))

        assert len(reviews) == 2
        assert all(isinstance(r, Review) for r in reviews)
        assert reviews[0].review_id == "r1"
        assert reviews[1].review_id == "r2"

    def test_empty_response_yields_nothing(self):
        client = self._make_client()
        client.http_client.get.return_value = {}

        reviews = list(client.list_reviews("accounts/1/locations/2"))

        assert reviews == []

    def test_empty_reviews_list_yields_nothing(self):
        client = self._make_client()
        client.http_client.get.return_value = {"reviews": []}

        reviews = list(client.list_reviews("accounts/1/locations/2"))

        assert reviews == []

    def test_multi_page_pagination(self):
        client = self._make_client()
        client.http_client.get.side_effect = [
            {"reviews": [self._review_data("r1")], "nextPageToken": "page2"},
            {"reviews": [self._review_data("r2")]},
        ]

        reviews = list(client.list_reviews("accounts/1/locations/2"))

        assert len(reviews) == 2
        assert reviews[0].review_id == "r1"
        assert reviews[1].review_id == "r2"
        assert client.http_client.get.call_count == 2

    def test_lazy_behavior_next_page_not_fetched_early(self):
        client = self._make_client()
        client.http_client.get.side_effect = [
            {"reviews": [self._review_data("r1"), self._review_data("r2")], "nextPageToken": "page2"},
            {"reviews": [self._review_data("r3")]},
        ]

        reviews = client.list_reviews("accounts/1/locations/2")
        first = next(reviews)
        assert first.review_id == "r1"
        assert client.http_client.get.call_count == 1

        remaining = list(reviews)
        assert len(remaining) == 2
        assert client.http_client.get.call_count == 2

    def test_passes_page_token_in_params(self):
        client = self._make_client()
        client.http_client.get.side_effect = [
            {"reviews": [self._review_data("r1")], "nextPageToken": "tok123"},
            {"reviews": []},
        ]

        list(client.list_reviews("accounts/1/locations/2"))

        second_call = client.http_client.get.call_args_list[1]
        params = second_call.kwargs.get("params", {})
        assert params.get("pageToken") == "tok123"

    def test_since_filters_old_reviews(self):
        """When since is set, reviews are ordered by updateTime desc and
        iteration stops as soon as we hit a review <= since (early exit).
        Mock data must reflect this desc ordering."""
        client = self._make_client()
        client.http_client.get.return_value = {
            "reviews": [
                self._review_data("new", update_time="2024-06-01T00:00:00Z"),
                self._review_data("old", update_time="2024-01-01T00:00:00Z"),
            ],
        }

        cutoff = datetime(2024, 3, 1, tzinfo=timezone.utc)
        reviews = list(client.list_reviews("accounts/1/locations/2", since=cutoff))

        assert len(reviews) == 1
        assert reviews[0].review_id == "new"

    def test_since_all_filtered_yields_nothing(self):
        client = self._make_client()
        client.http_client.get.return_value = {
            "reviews": [
                self._review_data("old", update_time="2024-01-01T00:00:00Z"),
            ],
        }

        cutoff = datetime(2024, 12, 1, tzinfo=timezone.utc)
        reviews = list(client.list_reviews("accounts/1/locations/2", since=cutoff))

        assert reviews == []

    def test_order_by_passes_to_api_params(self):
        client = self._make_client()
        client.http_client.get.return_value = {"reviews": [self._review_data("r1")]}

        list(client.list_reviews("accounts/1/locations/2", order_by="rating desc"))

        call_kwargs = client.http_client.get.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert params.get("orderBy") == "rating desc"

    def test_order_by_none_omits_param(self):
        client = self._make_client()
        client.http_client.get.return_value = {"reviews": []}

        list(client.list_reviews("accounts/1/locations/2"))

        call_kwargs = client.http_client.get.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert "orderBy" not in params

    def test_calls_correct_url(self):
        client = self._make_client()
        client.http_client.get.return_value = {"reviews": []}

        list(client.list_reviews("accounts/1/locations/2"))

        call_args = client.http_client.get.call_args
        url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        assert "mybusiness.googleapis.com/v4/accounts/1/locations/2/reviews" in url


class TestHttpxAuthRequest:
    def test_returns_httpx_response_with_correct_attributes(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"access_token": "tok"}'

        with patch("google_reviews_client.client.httpx.request", return_value=mock_response) as mock_request:
            request = _HttpxAuthRequest()
            response = request("https://oauth2.googleapis.com/token", method="POST", body=b"grant_type=refresh_token")

        mock_request.assert_called_once_with(
            "POST",
            "https://oauth2.googleapis.com/token",
            content=b"grant_type=refresh_token",
            headers=None,
            timeout=None,
        )
        assert response.status == 200
        assert response.headers == {"content-type": "application/json"}
        assert response.data == b'{"access_token": "tok"}'

    def test_response_is_concrete_not_abstract(self):
        """Verify _HttpxResponse is a concrete class, not abstract."""
        resp = _HttpxResponse(200, {}, b"")
        assert resp.status == 200
        assert resp.headers == {}
        assert resp.data == b""

    def test_passes_headers_and_timeout(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""

        with patch("google_reviews_client.client.httpx.request", return_value=mock_response) as mock_request:
            request = _HttpxAuthRequest()
            request("https://example.com", headers={"Authorization": "Basic abc"}, timeout=30)

        mock_request.assert_called_once_with(
            "GET", "https://example.com", content=None, headers={"Authorization": "Basic abc"}, timeout=30
        )
