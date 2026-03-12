from google_business_reviews.exceptions import (
    AuthenticationError,
    GoogleAPIError,
    GoogleBusinessError,
    HTTPError,
    NotFoundError,
    PermissionError,  # noqa: A004
    RateLimitError,
    ValidationError,
)


class TestGoogleBusinessError:
    def test_inherits_from_exception(self):
        assert issubclass(GoogleBusinessError, Exception)

    def test_message_and_body(self):
        err = GoogleBusinessError("something failed", body="response body")
        assert str(err) == "something failed"
        assert err.body == "response body"

    def test_defaults(self):
        err = GoogleBusinessError()
        assert str(err) == ""
        assert err.body == ""


class TestDomainExceptions:
    """All domain exceptions inherit from GoogleBusinessError and accept body."""

    def test_authentication_error_inherits(self):
        assert issubclass(AuthenticationError, GoogleBusinessError)

    def test_authentication_error_body(self):
        err = AuthenticationError("bad creds", body='{"error": "invalid"}')
        assert err.body == '{"error": "invalid"}'

    def test_permission_error_inherits(self):
        assert issubclass(PermissionError, GoogleBusinessError)

    def test_permission_error_body(self):
        err = PermissionError("forbidden", body='{"error": "forbidden"}')
        assert err.body == '{"error": "forbidden"}'

    def test_not_found_error_inherits(self):
        assert issubclass(NotFoundError, GoogleBusinessError)

    def test_not_found_error_body(self):
        err = NotFoundError("missing", body='{"error": "not found"}')
        assert err.body == '{"error": "not found"}'

    def test_validation_error_inherits(self):
        assert issubclass(ValidationError, GoogleBusinessError)

    def test_google_api_error_inherits(self):
        assert issubclass(GoogleAPIError, GoogleBusinessError)

    def test_google_api_error_body(self):
        err = GoogleAPIError("server error", body='{"error": "internal"}')
        assert err.body == '{"error": "internal"}'

    def test_rate_limit_error_inherits(self):
        assert issubclass(RateLimitError, GoogleBusinessError)

    def test_rate_limit_error_retry_after(self):
        err = RateLimitError("slow down", body='{"error": "rate limit"}', retry_after=30)
        assert err.retry_after == 30
        assert err.body == '{"error": "rate limit"}'

    def test_rate_limit_error_retry_after_default(self):
        err = RateLimitError("slow down", body="")
        assert err.retry_after is None


class TestHTTPError:
    """HTTPError is transport-level, NOT a GoogleBusinessError."""

    def test_does_not_inherit_google_business_error(self):
        assert not issubclass(HTTPError, GoogleBusinessError)

    def test_inherits_from_exception(self):
        assert issubclass(HTTPError, Exception)

    def test_attributes(self):
        err = HTTPError(404, '{"error": "not found"}')
        assert err.status_code == 404
        assert err.body == '{"error": "not found"}'

    def test_str_representation(self):
        err = HTTPError(500, "server error")
        assert "500" in str(err)
