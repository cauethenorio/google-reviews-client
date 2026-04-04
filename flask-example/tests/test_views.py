"""Tests for views blueprint and index route (INFRA-03)."""


class TestIndexPage:
    """Test the index route."""

    def test_index_page(self, client):
        """GET / returns 200 with expected content."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"app is running" in response.data

    def test_index_page_has_title(self, client):
        """Index page contains the app title."""
        response = client.get("/")
        assert b"Google Reviews Demo" in response.data
