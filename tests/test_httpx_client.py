from unittest.mock import MagicMock, patch

import httpx

from google_reviews_client.exceptions import HTTPError
from google_reviews_client.http_client.httpx_client import HttpxHTTPClient


class TestHttpxHTTPClient:
    def test_get_success(self):
        client = HttpxHTTPClient()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = {"accounts": []}

        with patch.object(client._client, "get", return_value=mock_response):
            result = client.get("https://example.com/api")

        assert result == {"accounts": []}

    def test_get_with_params_and_headers(self):
        client = HttpxHTTPClient()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = {"data": "ok"}

        with patch.object(client._client, "get", return_value=mock_response) as mock_get:
            result = client.get("https://example.com/api", params={"page": "1"}, headers={"Authorization": "Bearer x"})

        mock_get.assert_called_once_with(
            "https://example.com/api", params={"page": "1"}, headers={"Authorization": "Bearer x"}
        )
        assert result == {"data": "ok"}

    def test_get_non_2xx_raises_http_error(self):
        client = HttpxHTTPClient()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.is_success = False
        mock_response.text = '{"error": "not found"}'
        mock_response.headers = {"content-type": "application/json"}

        with patch.object(client._client, "get", return_value=mock_response):
            try:
                client.get("https://example.com/api")
                msg = "Expected HTTPError"
                raise AssertionError(msg)
            except HTTPError as e:
                assert e.status_code == 404
                assert e.body == '{"error": "not found"}'
                assert e.headers == {"content-type": "application/json"}

    def test_get_500_raises_http_error(self):
        client = HttpxHTTPClient()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.is_success = False
        mock_response.text = "Internal Server Error"
        mock_response.headers = {}

        with patch.object(client._client, "get", return_value=mock_response):
            try:
                client.get("https://example.com/api")
                msg = "Expected HTTPError"
                raise AssertionError(msg)
            except HTTPError as e:
                assert e.status_code == 500
                assert e.body == "Internal Server Error"
