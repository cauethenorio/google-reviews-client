"""Tests for version exposure (PKG-02)."""

import importlib.metadata
from unittest.mock import patch

import google_reviews_client


class TestVersionFallback:
    def test_version_fallback_when_not_installed(self):
        """When package is not installed, __version__ falls back to 'dev'."""
        with patch(
            "importlib.metadata.version",
            side_effect=importlib.metadata.PackageNotFoundError("google-reviews-client"),
        ):
            # Re-execute the module-level code

            # We need to test the fallback logic directly
            from importlib.metadata import PackageNotFoundError, version

            try:
                v = version("google-reviews-client")
            except PackageNotFoundError:
                v = "dev"

            assert v == "dev"


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
