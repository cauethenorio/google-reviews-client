from abc import ABC, abstractmethod


class BaseHTTPClient(ABC):
    """Auth-agnostic HTTP transport abstraction."""

    @abstractmethod
    def get(self, url: str, *, params: dict | None = None, headers: dict | None = None) -> dict:
        """Make a GET request. Returns parsed JSON dict on 2xx, raises HTTPError on non-2xx."""
