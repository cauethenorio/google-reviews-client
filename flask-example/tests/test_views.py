"""Tests for views blueprint: landing page, accounts, locations, reviews."""

from unittest import mock

from cookies import TOKEN_COOKIE_NAME
from google_reviews_client.exceptions import (
    AuthenticationError,
    GoogleAPIError,
    GooglePermissionError,
    NotFoundError,
    RateLimitError,
)


class TestLandingPage:
    """Test the landing page content and error display."""

    def test_landing_page_returns_200(self, client):
        """GET / returns 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_landing_page_has_title(self, client):
        """Landing page has Google Reviews Demo in an h1."""
        response = client.get("/")
        assert b"<h1" in response.data
        assert b"Google Reviews Demo" in response.data

    def test_landing_page_has_trust_statement(self, client):
        """Landing page contains trust/privacy statement (D-04)."""
        response = client.get("/")
        assert b"Nothing is stored on our servers" in response.data

    def test_landing_page_has_sign_in_button(self, client):
        """Landing page has Sign in with Google link to /login."""
        response = client.get("/")
        assert b"Sign in with Google" in response.data
        assert b'href="/login"' in response.data

    def test_landing_page_has_feature_list(self, client):
        """Landing page lists all three feature items."""
        response = client.get("/")
        assert b"Browse your Google Business Profile accounts" in response.data
        assert b"View locations for each account" in response.data
        assert b"Read and explore reviews" in response.data

    def test_landing_page_shows_session_expired_error(self, client):
        """GET /?error=session_expired shows expiry message."""
        response = client.get("/?error=session_expired")
        assert response.status_code == 200
        assert b"Your session has expired" in response.data

    def test_landing_page_shows_access_denied_error(self, client):
        """GET /?error=access_denied shows cancellation message."""
        response = client.get("/?error=access_denied")
        assert response.status_code == 200
        assert b"Sign-in was cancelled" in response.data

    def test_landing_page_shows_state_mismatch_error(self, client):
        """GET /?error=state_mismatch shows generic sign-in error."""
        response = client.get("/?error=state_mismatch")
        assert response.status_code == 200
        assert b"Something went wrong" in response.data

    def test_landing_page_shows_generic_error(self, client):
        """GET /?error=unknown_thing shows unexpected error message."""
        response = client.get("/?error=unknown_thing")
        assert response.status_code == 200
        assert b"An unexpected error occurred" in response.data

    def test_landing_page_no_error_without_param(self, client):
        """GET / without error param does not show alert."""
        response = client.get("/")
        assert b'role="alert"' not in response.data

    def test_landing_page_no_logout_link(self, client):
        """Landing page does not show Log out link (unauthenticated)."""
        response = client.get("/")
        assert b"Log out" not in response.data


class TestAccountsList:
    """Test the authenticated accounts list on GET / (DATA-01, DATA-05)."""

    @mock.patch("views.get_client")
    def test_authenticated_index_shows_accounts(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """Authenticated GET / shows account names."""
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/")
        assert response.status_code == 200
        assert b"Test Business" in response.data
        assert b"PERSONAL" in response.data

    @mock.patch("views.get_client")
    def test_authenticated_index_shows_account_links(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """Authenticated GET / contains links to account detail."""
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/")
        assert b"/account/111" in response.data

    @mock.patch("views.get_client")
    def test_authenticated_index_empty_accounts(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """Empty accounts list shows message."""
        mock_client.list_accounts.return_value = []
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/")
        assert b"No accounts found" in response.data

    @mock.patch("views.get_client")
    def test_authenticated_index_shows_logout(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """Authenticated GET / shows Log out link."""
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/")
        assert b"Log out" in response.data

    def test_unauthenticated_index_shows_landing(self, client):
        """GET / without cookie shows landing page."""
        response = client.get("/")
        assert b"Sign in with Google" in response.data


class TestAccountDetail:
    """Test the account detail page (DATA-02, DATA-05, UX-05)."""

    @mock.patch("views.get_client")
    def test_account_shows_locations(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """GET /account/111 lists locations with titles and store codes."""
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/account/111")
        assert response.status_code == 200
        assert b"Main Store" in response.data
        assert b"MAIN" in response.data

    @mock.patch("views.get_client")
    def test_account_shows_location_links(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """Location links include account ID."""
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/account/111")
        assert b"/location/aaa?account=111" in response.data

    @mock.patch("views.get_client")
    def test_account_empty_locations(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """Empty locations list shows message."""
        mock_client.list_locations.return_value = []
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/account/111")
        assert b"No locations found for this account" in response.data

    @mock.patch("views.get_client")
    def test_account_has_breadcrumb(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """Account page has breadcrumb navigation."""
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/account/111")
        assert b"Accounts" in response.data
        assert b'aria-label="Breadcrumb"' in response.data

    def test_account_requires_auth(self, client):
        """GET /account/111 without cookie redirects."""
        response = client.get("/account/111")
        assert response.status_code == 302


class TestLocationDetail:
    """Test the location detail page (UX-05)."""

    @mock.patch("views.get_client")
    def test_location_shows_details(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """GET /location/aaa?account=111 shows location details."""
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa?account=111")
        assert response.status_code == 200
        assert b"Main Store" in response.data

    @mock.patch("views.get_client")
    def test_location_has_view_reviews_button(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """Location page has View Reviews link."""
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa?account=111")
        assert b"View Reviews" in response.data
        assert b"/location/aaa/reviews?account=111" in response.data

    @mock.patch("views.get_client")
    def test_location_has_breadcrumb(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """Location page has breadcrumb navigation."""
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa?account=111")
        assert b'aria-label="Breadcrumb"' in response.data

    def test_location_without_account_param_redirects(self, client, authenticated_cookie):
        """GET /location/aaa without ?account= redirects to /."""
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa")
        assert response.status_code == 302

    def test_location_requires_auth(self, client):
        """GET /location/aaa?account=111 without cookie redirects."""
        response = client.get("/location/aaa?account=111")
        assert response.status_code == 302


class TestReviewsList:
    """Test the reviews list page (DATA-03, DATA-05, UX-05)."""

    @mock.patch("views.get_reviews_page")
    @mock.patch("views.get_client")
    def test_reviews_shows_review_content(
        self, mock_get_client, mock_get_page, client, authenticated_cookie, mock_client, sample_reviews
    ):
        """Reviews page shows reviewer name, comment, and rating."""
        mock_get_client.return_value = mock_client
        mock_get_page.return_value = (sample_reviews, None)
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa/reviews?account=111")
        assert response.status_code == 200
        assert b"Alice" in response.data
        assert b"Great place!" in response.data
        assert b"5 / 5" in response.data

    @mock.patch("views.get_reviews_page")
    @mock.patch("views.get_client")
    def test_reviews_shows_date_formatted(
        self, mock_get_client, mock_get_page, client, authenticated_cookie, mock_client, sample_reviews
    ):
        """Reviews page formats dates."""
        mock_get_client.return_value = mock_client
        mock_get_page.return_value = (sample_reviews, None)
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa/reviews?account=111")
        assert b"Mar 15, 2025" in response.data

    @mock.patch("views.get_reviews_page")
    @mock.patch("views.get_client")
    def test_reviews_shows_reply(
        self, mock_get_client, mock_get_page, client, authenticated_cookie, mock_client, sample_reviews
    ):
        """Reviews page shows owner replies."""
        mock_get_client.return_value = mock_client
        mock_get_page.return_value = (sample_reviews, None)
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa/reviews?account=111")
        assert b"Owner reply" in response.data
        assert b"Thank you!" in response.data

    @mock.patch("views.get_reviews_page")
    @mock.patch("views.get_client")
    def test_reviews_empty(
        self, mock_get_client, mock_get_page, client, authenticated_cookie, mock_client
    ):
        """Empty reviews shows message."""
        mock_get_client.return_value = mock_client
        mock_get_page.return_value = ([], None)
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa/reviews?account=111")
        assert b"No reviews yet for this location" in response.data

    @mock.patch("views.get_reviews_page")
    @mock.patch("views.get_client")
    def test_reviews_has_breadcrumb(
        self, mock_get_client, mock_get_page, client, authenticated_cookie, mock_client, sample_reviews
    ):
        """Reviews page has breadcrumb navigation."""
        mock_get_client.return_value = mock_client
        mock_get_page.return_value = (sample_reviews, None)
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa/reviews?account=111")
        assert b'aria-label="Breadcrumb"' in response.data

    def test_reviews_requires_auth(self, client):
        """GET /location/aaa/reviews?account=111 without cookie redirects."""
        response = client.get("/location/aaa/reviews?account=111")
        assert response.status_code == 302

    def test_reviews_without_account_param_redirects(self, client, authenticated_cookie):
        """GET /location/aaa/reviews without ?account= redirects to /."""
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa/reviews")
        assert response.status_code == 302


class TestReviewsPagination:
    """Test review pagination (DATA-04)."""

    @mock.patch("views.get_reviews_page")
    @mock.patch("views.get_client")
    def test_next_page_link_shown(
        self, mock_get_client, mock_get_page, client, authenticated_cookie, mock_client, sample_reviews
    ):
        """Next page link appears when there is a next token."""
        mock_get_client.return_value = mock_client
        mock_get_page.return_value = (sample_reviews, "next-tok")
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa/reviews?account=111")
        assert b"Next page" in response.data
        assert b"page_token=next-tok" in response.data

    @mock.patch("views.get_reviews_page")
    @mock.patch("views.get_client")
    def test_no_next_page_when_no_token(
        self, mock_get_client, mock_get_page, client, authenticated_cookie, mock_client, sample_reviews
    ):
        """No next page link when token is None."""
        mock_get_client.return_value = mock_client
        mock_get_page.return_value = (sample_reviews, None)
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa/reviews?account=111")
        assert b"Next page" not in response.data

    @mock.patch("views.get_reviews_page")
    @mock.patch("views.get_client")
    def test_page_token_passed_to_api(
        self, mock_get_client, mock_get_page, client, authenticated_cookie, mock_client, sample_reviews
    ):
        """page_token query param is forwarded to get_reviews_page."""
        mock_get_client.return_value = mock_client
        mock_get_page.return_value = (sample_reviews, None)
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        client.get("/location/aaa/reviews?account=111&page_token=tok1")
        mock_get_page.assert_called_once()
        call_args = mock_get_page.call_args
        assert call_args[0][2] == "tok1" or call_args[1].get("page_token") == "tok1"


class TestAPIErrors:
    """Test error handling for API exceptions (DATA-06)."""

    @mock.patch("views.get_client")
    def test_auth_error_redirects_to_login(
        self, mock_get_client, client, authenticated_cookie
    ):
        """AuthenticationError redirects to /login."""
        mock_get_client.return_value = mock.MagicMock(
            list_accounts=mock.MagicMock(side_effect=AuthenticationError("expired"))
        )
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/")
        assert response.status_code == 302
        assert "/login" in response.location

    @mock.patch("views.get_client")
    def test_permission_error_shows_banner(
        self, mock_get_client, client, authenticated_cookie
    ):
        """GooglePermissionError shows permission error banner."""
        mock_get_client.return_value = mock.MagicMock(
            list_accounts=mock.MagicMock(side_effect=GooglePermissionError("forbidden"))
        )
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/")
        assert response.status_code == 200
        assert b"permission" in response.data.lower()
        assert b'role="alert"' in response.data

    @mock.patch("views.get_client")
    def test_rate_limit_error_shows_banner(
        self, mock_get_client, client, authenticated_cookie
    ):
        """RateLimitError shows rate limit error banner."""
        mock_get_client.return_value = mock.MagicMock(
            list_accounts=mock.MagicMock(side_effect=RateLimitError("slow down"))
        )
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/")
        assert response.status_code == 200
        assert b"Too many requests" in response.data

    @mock.patch("views.get_client")
    def test_not_found_error_shows_banner(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """NotFoundError on account detail shows not found banner."""
        mock_client.list_accounts.side_effect = NotFoundError("gone")
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/account/111")
        assert response.status_code == 200
        assert b"Resource not found" in response.data

    @mock.patch("views.get_client")
    def test_server_error_shows_banner(
        self, mock_get_client, client, authenticated_cookie
    ):
        """GoogleAPIError shows temporary unavailable banner."""
        mock_get_client.return_value = mock.MagicMock(
            list_accounts=mock.MagicMock(side_effect=GoogleAPIError("server error"))
        )
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/")
        assert response.status_code == 200
        assert b"temporarily unavailable" in response.data


class TestBreadcrumbs:
    """Test breadcrumb navigation (UX-05)."""

    @mock.patch("views.get_client")
    def test_account_page_breadcrumb_has_accounts_link(
        self, mock_get_client, client, authenticated_cookie, mock_client
    ):
        """Account page breadcrumb contains link to accounts (/)."""
        mock_get_client.return_value = mock_client
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/account/111")
        assert b'href="/"' in response.data

    @mock.patch("views.get_reviews_page")
    @mock.patch("views.get_client")
    def test_reviews_page_breadcrumb_has_all_levels(
        self, mock_get_client, mock_get_page, client, authenticated_cookie, mock_client, sample_reviews
    ):
        """Reviews breadcrumb contains Accounts, account name, and location title."""
        mock_get_client.return_value = mock_client
        mock_get_page.return_value = (sample_reviews, None)
        client.set_cookie(TOKEN_COOKIE_NAME, authenticated_cookie)
        response = client.get("/location/aaa/reviews?account=111")
        assert b"Accounts" in response.data
        assert b"Test Business" in response.data
        assert b"Main Store" in response.data
