"""Tests for views blueprint: landing page and accounts page (UX-01, UX-02)."""

from cookies import TOKEN_COOKIE_NAME


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
