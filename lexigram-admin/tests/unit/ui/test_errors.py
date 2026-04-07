"""Tests for the errors module."""


from lexigram.ui.exceptions import (
    ErrorCategory,
    ErrorResponse,
    FieldError,
    htmx_error_response,
    not_found_error,
    permission_error,
    server_error,
    timeout_error,
    validation_error,
)
from lexigram.ui.core.zones import Zones


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_all_categories_exist(self):
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.NOT_FOUND.value == "not_found"
        assert ErrorCategory.PERMISSION.value == "permission"
        assert ErrorCategory.SERVER.value == "server"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.TIMEOUT.value == "timeout"


class TestFieldError:
    """Tests for FieldError dataclass."""

    def test_field_error_creation(self):
        err = FieldError(field="email", message="Invalid email format")
        assert err.field == "email"
        assert err.message == "Invalid email format"
        assert err.code is None

    def test_field_error_with_code(self):
        err = FieldError(
            field="age", message="Must be positive", code="positive_required",
        )
        assert err.code == "positive_required"


class TestErrorResponse:
    """Tests for ErrorResponse dataclass."""

    def test_error_response_creation(self):
        err = ErrorResponse(
            category=ErrorCategory.SERVER,
            title="Server Error",
            message="Something went wrong",
            status_code=500,
        )
        assert err.category == ErrorCategory.SERVER
        assert err.title == "Server Error"
        assert err.status_code == 500

    def test_to_toast_html_renders(self):
        err = ErrorResponse(
            category=ErrorCategory.NOT_FOUND,
            title="Not Found",
            message="Resource missing",
            status_code=404,
        )
        html = err.to_toast_html()
        assert "Not Found" in html or "Resource missing" in html

    def test_to_flash_html_includes_zone_id(self):
        err = ErrorResponse(
            category=ErrorCategory.SERVER,
            title="Error",
            message="Oops",
            status_code=500,
        )
        html = err.to_flash_html()
        assert Zones.FLASH.id in html
        assert "hx-swap-oob" in html

    def test_to_inline_errors_html_with_field_errors(self):
        err = ErrorResponse(
            category=ErrorCategory.VALIDATION,
            title="Validation Error",
            message="Fix errors",
            status_code=422,
            field_errors=[
                FieldError(field="email", message="Invalid"),
                FieldError(field="name", message="Required"),
            ],
        )
        html = err.to_inline_errors_html()
        assert "email" in html
        assert "Invalid" in html
        assert "name" in html
        assert "Required" in html

    def test_to_inline_errors_html_empty_when_no_errors(self):
        err = ErrorResponse(
            category=ErrorCategory.SERVER,
            title="Error",
            message="Oops",
            status_code=500,
        )
        html = err.to_inline_errors_html()
        assert html == ""

    def test_to_error_state_html_with_retry(self):
        err = ErrorResponse(
            category=ErrorCategory.SERVER,
            title="Error",
            message="Try again",
            status_code=500,
            can_retry=True,
            retry_url="/retry",
        )
        html = err.to_error_state_html()
        assert "Try Again" in html
        assert "hx-get" in html
        assert "/retry" in html


class TestFactoryFunctions:
    """Tests for error factory functions."""

    def test_validation_error(self):
        err = validation_error(
            message="Fix the form",
            field_errors=[FieldError("email", "Bad email")],
        )
        assert err.category == ErrorCategory.VALIDATION
        assert err.status_code == 422
        assert len(err.field_errors) == 1

    def test_not_found_error(self):
        err = not_found_error("User not found")
        assert err.category == ErrorCategory.NOT_FOUND
        assert err.status_code == 404
        assert "User not found" in err.message

    def test_permission_error(self):
        err = permission_error()
        assert err.category == ErrorCategory.PERMISSION
        assert err.status_code == 403

    def test_server_error(self):
        err = server_error(retry_url="/api/data")
        assert err.category == ErrorCategory.SERVER
        assert err.status_code == 500
        assert err.can_retry is True
        assert err.retry_url == "/api/data"

    def test_timeout_error(self):
        err = timeout_error()
        assert err.category == ErrorCategory.TIMEOUT
        assert err.status_code == 504
        assert err.can_retry is True


class TestHTMXErrorResponse:
    """Tests for htmx_error_response function."""

    def test_htmx_error_response_returns_tuple(self):
        err = server_error("Oops")
        html, status, headers = htmx_error_response(err)

        assert isinstance(html, str)
        assert status == 500
        assert isinstance(headers, dict)

    def test_htmx_error_response_includes_flash(self):
        err = not_found_error()
        html, status, headers = htmx_error_response(err, include_flash=True)

        assert Zones.FLASH.id in html

    def test_htmx_error_response_validation_includes_inline_errors(self):
        err = validation_error(field_errors=[FieldError("name", "Required")])
        html, status, headers = htmx_error_response(err)

        assert "error-name" in html
        assert "Required" in html
