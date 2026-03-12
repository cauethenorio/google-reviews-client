import httpx

from google_reviews_client.exceptions import HTTPError

from .base_client import BaseHTTPClient


class HttpxHTTPClient(BaseHTTPClient):
    """Default HTTP transport using httpx."""

    def __init__(self):
        self._client = httpx.Client()

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def get(self, url: str, *, params: dict | None = None, headers: dict | None = None) -> dict:
        response = self._client.get(url, params=params, headers=headers)
        if not response.is_success:
            raise HTTPError(response.status_code, response.text, headers=dict(response.headers))
        return response.json()
