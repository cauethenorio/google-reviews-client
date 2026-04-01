"""Tests for version exposure (PKG-02)."""

import importlib.metadata

import google_reviews_client


class TestVersion:
    def test_version_is_accessible(self):
        """__version__ is importable and non-empty."""
        assert hasattr(google_reviews_client, "__version__")
        assert isinstance(google_reviews_client.__version__, str)
        assert len(google_reviews_client.__version__) > 0

    def test_version_matches_metadata(self):
        """__version__ matches importlib.metadata (pyproject.toml source)."""
        metadata_version = importlib.metadata.version("google-reviews-client")
        assert google_reviews_client.__version__ == metadata_version

    def test_version_in_all(self):
        """__version__ is listed in __all__."""
        assert "__version__" in google_reviews_client.__all__

    def test_version_from_import(self):
        """Can import __version__ directly."""
        from google_reviews_client import __version__

        assert __version__ == google_reviews_client.__version__
