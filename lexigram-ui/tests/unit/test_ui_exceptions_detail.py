"""Tests for UI exceptions - factory functions and error responses."""

import pytest

from lexigram.ui.exceptions import (
    ErrorCategory,
    ErrorResponse,
    FieldError,
    UIError,
    htmx_error_response,
    not_found_error,
    permission_error,
    render_validation_errors,
    server_error,
    timeout_error,
    validation_error,
)


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_validation_category(self) -> None:
        """Test validation category value."""
        assert ErrorCategory.VALIDATION.value == "validation"

    def test_not_found_category(self) -> None:
        """Test not_found category value."""
        assert ErrorCategory.NOT_FOUND.value == "not_found"

    def test_permission_category(self) -> None:
        """Test permission category value."""
        assert ErrorCategory.PERMISSION.value == "permission"

    def test_server_category(self) -> None:
        """Test server category value."""
        assert ErrorCategory.SERVER.value == "server"

    def test_network_category(self) -> None:
        """Test network category value."""
        assert ErrorCategory.NETWORK.value == "network"

    def test_timeout_category(self) -> None:
        """Test timeout category value."""
        assert ErrorCategory.TIMEOUT.value == "timeout"


class TestFieldError:
    """Tests for FieldError dataclass."""

    def test_field_error_basic(self) -> None:
        """Test basic field error creation."""
        err = FieldError(field="email", message="Invalid email")
        assert err.field == "email"
        assert err.message == "Invalid email"

    def test_field_error_with_code(self) -> None:
        """Test field error with code."""
        err = FieldError(field="email", message="Invalid", code="INVALID_FORMAT")
        assert err.code == "INVALID_FORMAT"

    def test_field_error_code_none_by_default(self) -> None:
        """Test code defaults to None."""
        err = FieldError(field="email", message="Invalid")
        assert err.code is None


class TestErrorResponse:
    """Tests for ErrorResponse dataclass."""

    def test_error_response_basic(self) -> None:
        """Test basic error response creation."""
        resp = ErrorResponse(
            category=ErrorCategory.VALIDATION,
            title="Validation Failed",
            message="Please check your input",
            status_code=422,
        )
        assert resp.category == ErrorCategory.VALIDATION
        assert resp.title == "Validation Failed"
        assert resp.status_code == 422

    def test_error_response_field_errors(self) -> None:
        """Test error response with field errors."""
        field_errors = [
            FieldError(field="email", message="Invalid"),
            FieldError(field="password", message="Too short"),
        ]
        resp = ErrorResponse(
            category=ErrorCategory.VALIDATION,
            title="Validation Failed",
            message="Please check your input",
            field_errors=field_errors,
        )
        assert len(resp.field_errors) == 2

    def test_error_response_field_errors_empty_by_default(self) -> None:
        """Test field errors defaults to empty list."""
        resp = ErrorResponse(
            category=ErrorCategory.SERVER,
            title="Error",
            message="Server error",
        )
        assert resp.field_errors == []

    def test_error_response_retry_url(self) -> None:
        """Test retry URL is stored."""
        resp = ErrorResponse(
            category=ErrorCategory.SERVER,
            title="Error",
            message="Server error",
            can_retry=True,
            retry_url="/api/retry",
        )
        assert resp.retry_url == "/api/retry"


class TestValidationError:
    """Tests for validation_error factory."""

    def test_validation_error_default(self) -> None:
        """Test default validation error."""
        resp = validation_error()
        assert resp.category == ErrorCategory.VALIDATION
        assert resp.title == "Validation Error"
        assert resp.status_code == 422

    def test_validation_error_custom_message(self) -> None:
        """Test custom message."""
        resp = validation_error(message="Custom message")
        assert resp.message == "Custom message"

    def test_validation_error_with_field_errors(self) -> None:
        """Test with field errors."""
        field_errors = [FieldError(field="email", message="Invalid")]
        resp = validation_error(field_errors=field_errors)
        assert len(resp.field_errors) == 1


class TestNotFoundError:
    """Tests for not_found_error factory."""

    def test_not_found_default(self) -> None:
        """Test default not found error."""
        resp = not_found_error()
        assert resp.category == ErrorCategory.NOT_FOUND
        assert resp.title == "Not Found"
        assert resp.status_code == 404


class TestPermissionError:
    """Tests for permission_error factory."""

    def test_permission_default(self) -> None:
        """Test default permission error."""
        resp = permission_error()
        assert resp.category == ErrorCategory.PERMISSION
        assert resp.title == "Permission Denied"
        assert resp.status_code == 403


class TestServerError:
    """Tests for server_error factory."""

    def test_server_default(self) -> None:
        """Test default server error."""
        resp = server_error()
        assert resp.category == ErrorCategory.SERVER
        assert resp.title == "Server Error"
        assert resp.status_code == 500
        assert resp.can_retry is False

    def test_server_with_retry(self) -> None:
        """Test server error with retry URL."""
        resp = server_error(retry_url="/api/retry")
        assert resp.can_retry is True
        assert resp.retry_url == "/api/retry"


class TestTimeoutError:
    """Tests for timeout_error factory."""

    def test_timeout_default(self) -> None:
        """Test default timeout error."""
        resp = timeout_error()
        assert resp.category == ErrorCategory.TIMEOUT
        assert resp.title == "Request Timeout"
        assert resp.status_code == 504
        assert resp.can_retry is True


class TestRenderValidationErrors:
    """Tests for render_validation_errors function."""

    def test_render_empty_dict(self) -> None:
        """Test empty dictionary returns empty string."""
        result = render_validation_errors({})
        assert result == ""

    def test_render_single_error(self) -> None:
        """Test single field error."""
        result = render_validation_errors({"email": "Invalid email"})
        assert "email" in result
        assert "Invalid email" in result

    def test_render_multiple_errors(self) -> None:
        """Test multiple field errors."""
        errors = {"email": "Invalid", "name": "Required"}
        result = render_validation_errors(errors)
        assert "email" in result
        assert "name" in result

    def test_render_list_of_errors(self) -> None:
        """Test list of FieldError objects."""
        errors = [
            FieldError(field="email", message="Invalid"),
            FieldError(field="name", message="Required"),
        ]
        result = render_validation_errors(errors)
        assert "email" in result
        assert "name" in result

    def test_render_list_messages(self) -> None:
        """Test dict with list messages."""
        errors = {"email": ["Invalid", "Too long"]}
        result = render_validation_errors(errors)
        assert "Invalid" in result
        assert "Too long" in result

    def test_render_filter_by_field(self) -> None:
        """Test filtering by field name."""
        errors = {
            "email": "Invalid",
            "name": "Required",
        }
        result = render_validation_errors(errors, field_name="email")
        assert "email" in result
        assert "name" not in result


class TestHtmxErrorResponse:
    """Tests for htmx_error_response function."""

    def test_htmx_error_response_basic(self) -> None:
        """Test basic HTMX error response with flash."""
        error = not_found_error()
        html, status, headers = htmx_error_response(error, include_flash=True)
        assert status == 404
        assert "HX-Retarget" in headers
        assert "HX-Reswap" in headers

    def test_htmx_error_response_without_flash(self) -> None:
        """Test HTMX error without flash returns no retarget."""
        error = not_found_error()
        html, status, headers = htmx_error_response(error, include_flash=False)
        assert status == 404
        assert "HX-Retarget" not in headers
        assert "HX-Reswap" in headers

    def test_htmx_error_response_validation(self) -> None:
        """Test validation error response includes inline errors."""
        error = validation_error()
        html, status, headers = htmx_error_response(error)
        assert len(html) > 0


class TestExceptionsExports:
    """Tests for exceptions module exports."""

    def test_error_category_exported(self) -> None:
        """Test ErrorCategory is exported."""
        from lexigram.ui.exceptions import __all__

        assert "ErrorCategory" in __all__

    def test_error_response_exported(self) -> None:
        """Test ErrorResponse is exported."""
        from lexigram.ui.exceptions import __all__

        assert "ErrorResponse" in __all__

    def test_field_error_exported(self) -> None:
        """Test FieldError is exported."""
        from lexigram.ui.exceptions import __all__

        assert "FieldError" in __all__

    def test_ui_error_exported(self) -> None:
        """Test UIError is exported."""
        from lexigram.ui.exceptions import __all__

        assert "UIError" in __all__