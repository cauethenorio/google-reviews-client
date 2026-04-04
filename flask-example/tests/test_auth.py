"""Tests for auth blueprint: login, callback, logout, login_required (AUTH-01..04)."""

from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock

from cookies import TOKEN_COOKIE_NAME, decrypt_tokens


class TestLogin:
    """Test the /login route (AUTH-01)."""

    @mock.patch("auth.Flow")
    def test_login_redirects_to_google(self, mock_flow_cls, client):
        """GET /login returns 302 with Location pointing to Google."""
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?foo=bar",
            "mock-state",
        )
        mock_flow.code_verifier = "mock-verifier"
        mock_flow_cls.from_client_config.return_value = mock_flow

        response = client.get("/login")

        assert response.status_code == 302
        assert response.location.startswith("https://accounts.google.com")

    @mock.patch("auth.Flow")
    def test_login_sets_pending_cookie(self, mock_flow_cls, client):
        """GET /login sets greviews_tokens cookie."""
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth",
            "mock-state",
        )
        mock_flow.code_verifier = "mock-verifier"
        mock_flow_cls.from_client_config.return_value = mock_flow

        response = client.get("/login")

        cookie_header = response.headers.get("Set-Cookie", "")
        assert TOKEN_COOKIE_NAME in cookie_header

    @mock.patch("auth.Flow")
    def test_login_includes_pkce_state_in_cookie(self, mock_flow_cls, client, fernet):
        """Pending cookie contains auth_status=pending, state, and verifier."""
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth",
            "test-state-123",
        )
        mock_flow.code_verifier = "test-verifier-456"
        mock_flow_cls.from_client_config.return_value = mock_flow

        response = client.get("/login")

        # Extract cookie value from Set-Cookie header
        cookie_header = response.headers.get("Set-Cookie", "")
        # Parse the cookie value (format: name=value; ...)
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith(f"{TOKEN_COOKIE_NAME}="):
                cookie_value = part.split("=", 1)[1]
                break

        data = decrypt_tokens(cookie_value, fernet)
        assert data is not None
        assert data["auth_status"] == "pending"
        assert data["state"] == "test-state-123"
        assert data["verifier"] == "test-verifier-456"

    @mock.patch("auth.Flow")
    def test_login_uses_offline_access(self, mock_flow_cls, client):
        """Flow.authorization_url called with access_type=offline and prompt=consent."""
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth",
            "mock-state",
        )
        mock_flow.code_verifier = "mock-verifier"
        mock_flow_cls.from_client_config.return_value = mock_flow

        client.get("/login")

        mock_flow.authorization_url.assert_called_once_with(
            access_type="offline", prompt="consent"
        )


class TestCallback:
    """Test the /callback route (AUTH-02)."""

    def test_callback_without_cookie_redirects_with_error(self, client):
        """GET /callback with no cookie redirects to /?error=missing_state."""
        response = client.get("/callback?state=x&code=y")
        assert response.status_code == 302
        assert response.location.endswith("/?error=missing_state")

    def test_callback_with_state_mismatch_redirects(self, client, pending_cookie):
        """Mismatched state param redirects to /?error=state_mismatch."""
        client.set_cookie(TOKEN_COOKIE_NAME, pending_cookie)
        response = client.get("/callback?state=wrong-state&code=y")
        assert response.status_code == 302
        assert "error=state_mismatch" in response.location

    def test_callback_with_google_error_redirects(self, client, pending_cookie):
        """Google error param is forwarded to landing page."""
        client.set_cookie(TOKEN_COOKIE_NAME, pending_cookie)
        response = client.get(
            "/callback?error=access_denied&state=test-state-value"
        )
        assert response.status_code == 302
        assert "error=access_denied" in response.location

    @mock.patch("auth.Flow")
    def test_callback_success_sets_authenticated_cookie(
        self, mock_flow_cls, client, pending_cookie, fernet
    ):
        """Successful callback renders success page with meta refresh."""
        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.token = "access-tok"
        mock_creds.refresh_token = "refresh-tok"
        mock_creds.expiry = datetime(2099, 1, 1)
        mock_flow.credentials = mock_creds
        mock_flow_cls.from_client_config.return_value = mock_flow

        client.set_cookie(TOKEN_COOKIE_NAME, pending_cookie)
        response = client.get(
            "/callback?state=test-state-value&code=auth-code"
        )

        assert response.status_code == 200
        assert b"Authenticated successfully!" in response.data
        assert b'meta http-equiv="refresh"' in response.data

        # Verify the cookie contains authenticated data
        cookie_header = response.headers.get("Set-Cookie", "")
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith(f"{TOKEN_COOKIE_NAME}="):
                cookie_value = part.split("=", 1)[1]
                break

        data = decrypt_tokens(cookie_value, fernet)
        assert data is not None
        assert data["auth_status"] == "authenticated"
        assert data["access_token"] == "access-tok"
        assert data["refresh_token"] == "refresh-tok"
        assert "expiry" in data


class TestLogout:
    """Test the /logout route (AUTH-03)."""

    def test_logout_redirects_to_index(self, client):
        """GET /logout returns 302 to /."""
        response = client.get("/logout")
        assert response.status_code == 302
        assert response.location.endswith("/")

    def test_logout_clears_cookie(self, client):
        """GET /logout expires/clears the greviews_tokens cookie."""
        response = client.get("/logout")
        cookie_header = response.headers.get("Set-Cookie", "")
        assert TOKEN_COOKIE_NAME in cookie_header
        # Flask delete_cookie sets Expires to epoch 0 or max-age=0
        header_lower = cookie_header.lower()
        assert "expires=" in header_lower or "max-age=0" in header_lower


class TestLoginRequired:
    """Test the login_required decorator (AUTH-04)."""

    def test_protected_route_without_cookie_redirects(self, client):
        """GET /account/111 with no cookie redirects to /?error=session_expired."""
        response = client.get("/account/111")
        assert response.status_code == 302
        assert "error=session_expired" in response.location

    def test_protected_route_with_invalid_cookie_redirects(self, client):
        """GET /account/111 with garbage cookie redirects to /?error=session_expired."""
        client.set_cookie(TOKEN_COOKIE_NAME, "not-valid-fernet-data")
        response = client.get("/account/111")
        assert response.status_code == 302
        assert "error=session_expired" in response.location

    def test_protected_route_with_pending_cookie_redirects(self, client, pending_cookie):
        """GET /account/111 with pending cookie redirects (not authenticated)."""
        client.set_cookie(TOKEN_COOKIE_NAME, pending_cookie)
        response = client.get("/account/111")
        assert response.status_code == 302
        assert "error=session_expired" in response.location
