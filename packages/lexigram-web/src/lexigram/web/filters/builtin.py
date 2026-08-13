"""Built-in exception filters for Lexigram Web."""

from __future__ import annotations

import dataclasses
from typing import Any

from lexigram.web.errors.html_error_renderer import DebugHtmlErrorRenderer
from lexigram.web.exceptions import (
    DependencyResolutionError,
    HTTPError,
)
from lexigram.web.transport.responses import JSONResponse


class ValidationErrorFilter:
    """Filter for handling Pydantic and Lexigram validation errors."""

    def can_handle(self, exc: Exception) -> bool:
        """Check if exception is a validation error."""
        name = exc.__class__.__name__
        return (
            name in ("ValidationError", "PydanticValidationError")
            or getattr(exc, "code", None) in ("validation_error", "VALIDATION_ERROR")
            or (
                isinstance(exc, ValueError)
                and any(kw in str(exc) for kw in ("validation", "Invalid", "coercion"))
            )
        )

    async def handle(self, exc: Any, _request: Any) -> JSONResponse:
        """Transform ValidationError into a 422 JSONResponse with RFC 7807 format."""
        raw_errors: list[Any] = []
        if hasattr(exc, "errors") and callable(exc.errors):
            raw_errors = exc.errors()
        elif hasattr(exc, "errors") and isinstance(exc.errors, list):
            raw_errors = exc.errors
        elif hasattr(exc, "args") and exc.args:
            raw_errors = [{"msg": str(arg)} for arg in exc.args]

        errors = []
        for e in raw_errors:
            if dataclasses.is_dataclass(e) and not isinstance(e, type):
                errors.append(dataclasses.asdict(e))
            elif isinstance(e, dict):
                errors.append(e)
            elif hasattr(e, "field") and hasattr(e, "message"):
                errors.append(
                    {
                        "field": e.field,
                        "message": e.message,
                        "code": getattr(e, "code", None),
                    }
                )
            else:
                errors.append({"msg": str(e)})

        from lexigram.web.errors.problem_detail import ProblemDetail

        pd = ProblemDetail(
            type="urn:lexigram:validation-error",
            title="Validation Error",
            status=422,
            detail="Request validation failed",
            errors=errors,
        )
        return JSONResponse(
            content=pd.to_dict(),
            status_code=422,
            media_type="application/problem+json",
        )


class DependencyResolutionFilter:
    """Filter for handling DependencyResolutionError."""

    def can_handle(self, exc: Exception) -> bool:
        """Check if exception is a DependencyResolutionError."""
        return (
            isinstance(exc, DependencyResolutionError)
            or exc.__class__.__name__ == "DependencyResolutionError"
            or getattr(exc, "code", None) == "dependency_resolution_error"
        )

    async def handle(self, exc: Any, _request: Any) -> JSONResponse:
        """Transform DependencyResolutionError into a 500 RFC 7807 JSONResponse."""
        from lexigram.web.errors.problem_detail import ProblemDetail

        pd = ProblemDetail.internal_error(detail=getattr(exc, "detail", str(exc)))
        return JSONResponse(
            content=pd.to_dict(),
            status_code=500,
            media_type="application/problem+json",
        )


class DefaultExceptionFilter:
    """Default filter that handles HTTPError and generic exceptions.

    When ``debug=True`` and the HTTP client sends ``Accept: text/html``,
    the response is a rich HTML error page showing the traceback and request
    details.  In all other cases a structured JSON response is returned.
    """

    def __init__(self, debug: bool = False) -> None:
        """Initialise the filter.

        Args:
            debug: When ``True``, HTML error pages are rendered for browser
                clients.  Set this based on ``ServerConfig.debug`` or
                the ``LEX_DEBUG`` environment variable.
        """
        self._debug = debug
        self._html_renderer = DebugHtmlErrorRenderer()

    def can_handle(self, exc: Exception) -> bool:
        """Handle HTTPErrors and LexigramErrors specifically."""
        from lexigram.contracts.exceptions import LexigramError

        return (
            isinstance(exc, (HTTPError, LexigramError))
            or getattr(exc, "status_code", None) is not None
            or hasattr(exc, "code")
        )

    async def handle(self, exc: Exception, request: Any) -> Any:
        """Transform the exception into a JSON or HTML response.

        When ``debug=True`` and the request prefers HTML, a rich debug page
        is returned instead of JSON.  All JSON responses use RFC 7807
        ``application/problem+json`` format.
        """
        from lexigram.web.errors.problem_detail import ProblemDetail

        if isinstance(exc, HTTPError):
            if self._debug and self._html_renderer.should_render(request):
                return self._html_renderer.render(
                    exc,
                    request,
                    status_code=exc.status_code,
                    title=f"{exc.status_code} {exc.detail}",
                )
            code = getattr(exc, "code", None)
            pd = ProblemDetail(
                type=(
                    f"urn:lexigram:{code.lower().replace('_', '-')}"
                    if code
                    else "about:blank"
                ),
                title=exc.detail,
                status=exc.status_code,
                detail=exc.detail,
            )
            return JSONResponse(
                content=pd.to_dict(),
                status_code=exc.status_code,
                headers=exc.headers,
                media_type="application/problem+json",
            )

        # Handle domain errors via MRO-ordered type mapping.
        from lexigram.contracts.exceptions.domain import (
            AuthenticationError,
            AuthorizationError,
            ConflictError,
            DomainError,
            NotFoundError,
            PermissionDeniedError,
        )

        status_code = 500
        type_uri = "urn:lexigram:internal-error"
        title = "Internal Server Error"

        if isinstance(exc, NotFoundError):
            status_code, type_uri, title = 404, "urn:lexigram:not-found", "Not Found"
        elif isinstance(exc, (PermissionDeniedError, AuthorizationError)):
            status_code, type_uri, title = 403, "urn:lexigram:forbidden", "Forbidden"
        elif isinstance(exc, AuthenticationError):
            status_code, type_uri, title = (
                401,
                "urn:lexigram:unauthorized",
                "Unauthorized",
            )
        elif isinstance(exc, ConflictError):
            status_code, type_uri, title = 409, "urn:lexigram:conflict", "Conflict"
        elif isinstance(exc, DomainError):
            status_code, type_uri, title = (
                400,
                "urn:lexigram:bad-request",
                "Bad Request",
            )

        if self._debug and self._html_renderer.should_render(request):
            return self._html_renderer.render(exc, request, status_code=status_code)

        pd = ProblemDetail(
            type=type_uri,
            title=title,
            status=status_code,
            detail=str(exc),
        )
        return JSONResponse(
            content=pd.to_dict(),
            status_code=status_code,
            media_type="application/problem+json",
        )


__all__ = [
    "DefaultExceptionFilter",
    "DependencyResolutionFilter",
    "ValidationErrorFilter",
]
