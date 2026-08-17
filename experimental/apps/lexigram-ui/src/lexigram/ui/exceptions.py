"""UI package exceptions and standardized error responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from lexigram.contracts.exceptions import LexigramError
from lexigram.ui.core.base import el, render_to_string
from lexigram.ui.core.zones import Zones
from lexigram.ui.molecules.error_state import ErrorState
from lexigram.ui.molecules.toast import InlineToast


class UIError(LexigramError):
    """Base exception for all UI-domain errors."""

    _code: str = "LEX_ERR_UI_001"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code

    def __str__(self) -> str:
        """Return plain message without code prefix — safe for UI-facing output."""
        return self.message


class ErrorCategory(str, Enum):
    """Categories of errors with different handling strategies."""

    VALIDATION = "validation"  # 422 - Inline field errors
    NOT_FOUND = "not_found"  # 404 - Toast + stay on page
    PERMISSION = "permission"  # 403 - Toast + disable action
    SERVER = "server"  # 500 - Toast + retry option
    NETWORK = "network"  # Connection issues
    TIMEOUT = "timeout"  # 408/504 - Toast + retry button


@dataclass
class FieldError:
    """Error for a specific form field."""

    field: str
    message: str
    code: str | None = None


@dataclass
class ErrorResponse:
    """Standardized error response for HTMX."""

    category: ErrorCategory
    title: str
    message: str
    status_code: int = 500
    field_errors: list[FieldError] = field(default_factory=list)
    retry_url: str | None = None
    can_retry: bool = False

    def to_toast_html(self) -> str:
        """Render as a toast notification."""
        variant_map = {
            ErrorCategory.VALIDATION: "warning",
            ErrorCategory.NOT_FOUND: "error",
            ErrorCategory.PERMISSION: "error",
            ErrorCategory.SERVER: "error",
            ErrorCategory.NETWORK: "warning",
            ErrorCategory.TIMEOUT: "warning",
        }

        toast = InlineToast(
            message=self.message,
            toast_type=variant_map.get(self.category, "error"),
        )

        return render_to_string(toast)

    def to_flash_html(self) -> str:
        """Render as an OOB flash message targeting the flash container."""
        toast_html = self.to_toast_html()
        return render_to_string(
            el(
                "div",
                toast_html,
                id=Zones.FLASH.id,
                hx_swap_oob="innerHTML",
            ),
        )

    def to_inline_errors_html(self) -> str:
        """Render field errors for form validation."""
        if not self.field_errors:
            return ""

        errors_html = []
        for err in self.field_errors:
            errors_html.append(
                el(
                    "div",
                    el("span", f"{err.field}: ", class_="font-medium"),
                    err.message,
                    class_="text-sm text-destructive",
                    id=f"error-{err.field}",
                ),
            )

        return render_to_string(el("div", *errors_html, class_="space-y-1"))

    def to_error_state_html(self) -> str:
        """Render as a full error state component."""
        action = None
        if self.can_retry and self.retry_url:
            action = el(
                "button",
                "Try Again",
                class_="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors",
                hx_get=self.retry_url,
                hx_target=Zones.DATA.selector,
                hx_swap=Zones.DATA.swap_mode.value,
            )

        return render_to_string(
            ErrorState(
                title=self.title,
                message=self.message,
                action=action,
            ),
        )


# Factory functions for common error types


def validation_error(
    message: str = "Please correct the errors below.",
    field_errors: list[FieldError] | None = None,
) -> ErrorResponse:
    """Create a validation error response (422)."""
    return ErrorResponse(
        category=ErrorCategory.VALIDATION,
        title="Validation Error",
        message=message,
        status_code=422,
        field_errors=field_errors or [],
    )


def not_found_error(
    message: str = "The requested resource was not found.",
) -> ErrorResponse:
    """Create a not found error response (404)."""
    return ErrorResponse(
        category=ErrorCategory.NOT_FOUND,
        title="Not Found",
        message=message,
        status_code=404,
    )


def permission_error(
    message: str = "You don't have permission to perform this action.",
) -> ErrorResponse:
    """Create a permission error response (403)."""
    return ErrorResponse(
        category=ErrorCategory.PERMISSION,
        title="Permission Denied",
        message=message,
        status_code=403,
    )


def server_error(
    message: str = "An unexpected error occurred. Please try again.",
    retry_url: str | None = None,
) -> ErrorResponse:
    """Create a server error response (500)."""
    return ErrorResponse(
        category=ErrorCategory.SERVER,
        title="Server Error",
        message=message,
        status_code=500,
        can_retry=retry_url is not None,
        retry_url=retry_url,
    )


def timeout_error(
    message: str = "The request timed out. Please try again.",
    retry_url: str | None = None,
) -> ErrorResponse:
    """Create a timeout error response (504)."""
    return ErrorResponse(
        category=ErrorCategory.TIMEOUT,
        title="Request Timeout",
        message=message,
        status_code=504,
        can_retry=True,
        retry_url=retry_url,
    )


def render_validation_errors(
    errors: list[FieldError] | dict[str, str | list[str]],
    field_name: str | None = None,
) -> str:
    """Render validation errors as an HTML string."""
    normalised: list[FieldError]

    if isinstance(errors, dict):
        normalised = []
        for field, messages in errors.items():
            if isinstance(messages, list):
                for msg in messages:
                    normalised.append(FieldError(field=field, message=str(msg)))
            else:
                normalised.append(FieldError(field=field, message=str(messages)))
    else:
        normalised = list(errors)

    if field_name is not None:
        normalised = [e for e in normalised if e.field == field_name]

    if not normalised:
        return ""

    items = [
        el(
            "div",
            el("span", f"{err.field}: ", class_="font-medium"),
            err.message,
            class_="text-sm text-destructive",
            id=f"error-{err.field}",
        )
        for err in normalised
    ]
    return render_to_string(el("div", *items, class_="space-y-1"))


def htmx_error_response(
    error: ErrorResponse,
    include_flash: bool = True,
) -> tuple[str, int, dict]:
    """Build an HTMX-compatible error response."""
    html_parts = []

    # Include flash/toast notification
    if include_flash:
        html_parts.append(error.to_flash_html())

    # For validation errors, return inline errors
    if error.category == ErrorCategory.VALIDATION:
        html_parts.append(error.to_inline_errors_html())
    else:
        # For other errors, optionally include error state
        html_parts.append(error.to_error_state_html())

    html = "".join(html_parts)

    headers = {
        "HX-Retarget": Zones.FLASH.selector if include_flash else None,
        "HX-Reswap": "innerHTML",
    }
    # Remove None headers
    headers = {k: v for k, v in headers.items() if v is not None}

    return html, error.status_code, headers


__all__ = [
    "ErrorCategory",
    "ErrorResponse",
    "FieldError",
    "UIError",
    "htmx_error_response",
    "not_found_error",
    "permission_error",
    "render_validation_errors",
    "server_error",
    "timeout_error",
    "validation_error",
]
