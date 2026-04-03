"""Regression tests for previously-fixed bugs (TEST-01, TEST-02)."""

import pathlib
from unittest.mock import Mock

from google_reviews_client.client import GoogleReviewsClient
from google_reviews_client.http_client import BaseHTTPClient


class TestEmptyApiResponses:
    """TEST-01: Empty API responses must not raise KeyError.

    The Google API returns {} instead of {"accounts": []} (or similar)
    when there are no results. The client must handle this gracefully.
    """

    def _make_client(self):
        """Create a GoogleReviewsClient with a mocked HTTP client returning {}."""
        creds = Mock()
        creds.before_request = Mock()
        client = GoogleReviewsClient(credentials=creds)
        client.http_client = Mock(spec=BaseHTTPClient)
        client.http_client.get.return_value = {}
        return client

    def test_list_accounts_empty_response(self):
        """list_accounts returns [] when API returns {} (no 'accounts' key)."""
        client = self._make_client()
        result = client.list_accounts()
        assert result == []

    def test_list_locations_empty_response(self):
        """list_locations returns [] when API returns {} (no 'locations' key)."""
        client = self._make_client()
        result = client.list_locations("accounts/123")
        assert result == []

    def test_list_reviews_empty_response(self):
        """list_reviews yields nothing when API returns {} (no 'reviews' key, no 'nextPageToken')."""
        client = self._make_client()
        result = list(client.list_reviews("accounts/123/locations/456"))
        assert result == []


class TestNoBreakpointsInSource:
    """TEST-02: No debugging statements in production code."""

    def test_no_breakpoints_in_source(self):
        """Scan all .py files under src/google_reviews_client/ for debug statements."""
        src_root = pathlib.Path(__file__).resolve().parent.parent / "src" / "google_reviews_client"
        forbidden = ("breakpoint()", "pdb.set_trace()", "import pdb", "from pdb import")
        violations = []

        for py_file in src_root.rglob("*.py"):
            lines = py_file.read_text().splitlines()
            for line_num, line in enumerate(lines, start=1):
                stripped = line.strip()
                # Skip comments
                if stripped.startswith("#"):
                    continue
                for pattern in forbidden:
                    if pattern in stripped:
                        violations.append(f"{py_file.relative_to(src_root.parent.parent)}:{line_num}: {stripped}")

        assert not violations, "Found debugging statements in production code:\n" + "\n".join(violations)
