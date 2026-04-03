from unittest.mock import MagicMock, call, patch

import httpx
import pytest

from google_reviews_client.exceptions import HTTPError
from google_reviews_client.http_client.httpx_client import HttpxHTTPClient


def _mock_response(*, status_code, is_success=None, json_data=None, text="", headers=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_success = is_success if is_success is not None else (200 <= status_code < 300)
    resp.text = text
    resp.content = text.encode() if isinstance(text, str) else b""
    resp.headers = httpx.Headers(headers or {})
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


class TestHttpxHTTPClient:
    def test_get_success(self):
        client = HttpxHTTPClient()
        mock_resp = _mock_response(status_code=200, json_data={"accounts": []})

        with patch.object(client._client, "get", return_value=mock_resp):
            result = client.get("https://example.com/api")

        assert result == {"accounts": []}

    def test_get_with_params_and_headers(self):
        client = HttpxHTTPClient()
        mock_resp = _mock_response(status_code=200, json_data={"data": "ok"})

        with patch.object(client._client, "get", return_value=mock_resp) as mock_get:
            result = client.get("https://example.com/api", params={"page": "1"}, headers={"Authorization": "Bearer x"})

        mock_get.assert_called_once_with(
            "https://example.com/api", params={"page": "1"}, headers={"Authorization": "Bearer x"}
        )
        assert result == {"data": "ok"}

    def test_non_retryable_error_raises_immediately(self):
        client = HttpxHTTPClient()
        mock_resp = _mock_response(
            status_code=404, text='{"error": "not found"}', headers={"content-type": "application/json"}
        )

        with patch.object(client._client, "get", return_value=mock_resp) as mock_get:
            with pytest.raises(HTTPError) as exc_info:
                client.get("https://example.com/api")

            assert exc_info.value.status_code == 404
            assert exc_info.value.body == '{"error": "not found"}'
            assert mock_get.call_count == 1


class TestParseRetryAfter:
    def test_parse_retry_after_non_numeric(self):
        from google_reviews_client.http_client.httpx_client import _parse_retry_after

        headers = httpx.Headers({"retry-after": "not-a-number"})
        assert _parse_retry_after(headers) is None

    def test_parse_retry_after_missing(self):
        from google_reviews_client.http_client.httpx_client import _parse_retry_after

        headers = httpx.Headers({})
        assert _parse_retry_after(headers) is None


class TestHttpxHTTPClientContextManager:
    def test_context_manager_protocol(self):
        client = HttpxHTTPClient()
        with patch.object(client, "close") as mock_close:
            with client as ctx:
                assert ctx is client
            mock_close.assert_called_once()

    def test_close_method(self):
        client = HttpxHTTPClient()
        with patch.object(client._client, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()


class TestHttpxHTTPClientRetry:
    def test_retries_on_500_then_succeeds(self):
        client = HttpxHTTPClient(backoff_base=0.0)
        fail = _mock_response(status_code=500, text="error")
        ok = _mock_response(status_code=200, json_data={"ok": True})

        with patch.object(client._client, "get", side_effect=[fail, ok]):
            result = client.get("https://example.com/api")

        assert result == {"ok": True}

    def test_retries_on_429_then_succeeds(self):
        client = HttpxHTTPClient(backoff_base=0.0)
        fail = _mock_response(status_code=429, text="rate limited")
        ok = _mock_response(status_code=200, json_data={"ok": True})

        with patch.object(client._client, "get", side_effect=[fail, ok]):
            result = client.get("https://example.com/api")

        assert result == {"ok": True}

    def test_retries_on_502_503_504(self):
        for status in (502, 503, 504):
            client = HttpxHTTPClient(backoff_base=0.0)
            fail = _mock_response(status_code=status, text="error")
            ok = _mock_response(status_code=200, json_data={"ok": True})

            with patch.object(client._client, "get", side_effect=[fail, ok]):
                result = client.get("https://example.com/api")

            assert result == {"ok": True}

    def test_raises_after_max_retries_exhausted(self):
        client = HttpxHTTPClient(max_retries=2, backoff_base=0.0)
        fail = _mock_response(status_code=500, text="error")

        with patch.object(client._client, "get", return_value=fail) as mock_get:
            with pytest.raises(HTTPError) as exc_info:
                client.get("https://example.com/api")

            assert exc_info.value.status_code == 500
            assert mock_get.call_count == 3  # 1 initial + 2 retries

    def test_respects_retry_after_header(self):
        client = HttpxHTTPClient(max_retries=1, backoff_base=0.0)
        fail = _mock_response(status_code=429, text="rate limited", headers={"Retry-After": "5"})
        ok = _mock_response(status_code=200, json_data={"ok": True})

        with (
            patch.object(client._client, "get", side_effect=[fail, ok]),
            patch("google_reviews_client.http_client.httpx_client.time.sleep") as mock_sleep,
        ):
            client.get("https://example.com/api")

        mock_sleep.assert_called_once_with(5.0)

    def test_uses_exponential_backoff_without_retry_after(self):
        client = HttpxHTTPClient(max_retries=3, backoff_base=1.0)
        fail = _mock_response(status_code=500, text="error")
        ok = _mock_response(status_code=200, json_data={"ok": True})

        with (
            patch.object(client._client, "get", side_effect=[fail, fail, ok]),
            patch("google_reviews_client.http_client.httpx_client.time.sleep") as mock_sleep,
        ):
            client.get("https://example.com/api")

        assert mock_sleep.call_args_list == [call(1.0), call(2.0)]

    def test_no_retries_when_max_retries_zero(self):
        client = HttpxHTTPClient(max_retries=0)
        fail = _mock_response(status_code=500, text="error")

        with patch.object(client._client, "get", return_value=fail) as mock_get:
            with pytest.raises(HTTPError) as exc_info:
                client.get("https://example.com/api")

            assert exc_info.value.status_code == 500
            assert mock_get.call_count == 1
