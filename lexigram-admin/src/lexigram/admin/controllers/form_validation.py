"""Form validation and autocomplete controller for real-time features."""

from __future__ import annotations

import asyncio
from typing import Any

from starlette.responses import HTMLResponse, JSONResponse

from lexigram.admin.controllers.base import AdminController
from lexigram.contracts.web import get, post
from lexigram.di.decorators import inject


@inject
class FormValidationController(AdminController):
    """Controller for real-time form validation and autocomplete."""

    def __init__(self, renderer: Any) -> None:
        super().__init__(renderer)

    @post("/api/forms/validate/{field_name}")
    async def validate_field(self, field_name: str, request) -> Any:
        """Validate a single field in real-time."""
        try:
            # Get form data from request
            if request.headers.get("content-type") == "application/json":
                data = await request.json()
            else:
                form_data = await request.form()
                data = dict(form_data)

            field_value = data.get(field_name)

            # For now, return success - in a real implementation,
            # you'd look up the field from a form registry and validate it
            # This is a placeholder for the real-time validation endpoint

            # Simulate async validation delay
            if field_name == "email":
                await asyncio.sleep(0.1)  # Simulate API call
                if field_value and "@" not in field_value:
                    return HTMLResponse(
                        content='<span class="text-red-500 text-sm">Invalid email address</span>',
                        status_code=200,
                    )

            return HTMLResponse(content="", status_code=200)  # Clear any previous error

        except Exception as e:  # noqa: BLE001 — controller boundary; all errors become HTTP 400 responses
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.exception("Field validation error for %s", field_name)
            return HTMLResponse(
                content=f'<span class="text-red-500 text-sm">Validation error: {e!s}</span>',
                status_code=400,
            )

    @get("/api/forms/autocomplete/{field_name}")
    async def autocomplete_field(self, field_name: str, request) -> Any:
        """Provide autocomplete suggestions for a field."""
        try:
            query = request.query_params.get("q", "")

            # Simulate autocomplete data based on field name
            suggestions = []

            if field_name == "country":
                countries = [
                    "United States",
                    "United Kingdom",
                    "Canada",
                    "Australia",
                    "Germany",
                    "France",
                ]
                suggestions = list(
                    filter(lambda c: query.lower() in c.lower(), countries),
                )
            elif field_name == "city":
                cities = ["New York", "London", "Toronto", "Sydney", "Berlin", "Paris"]
                suggestions = list(filter(lambda c: query.lower() in c.lower(), cities))
            elif field_name == "tags":
                tags = [
                    "urgent",
                    "important",
                    "review",
                    "draft",
                    "published",
                    "archived",
                ]
                suggestions = list(filter(lambda t: query.lower() in t.lower(), tags))

            # Return HTML for HTMX to swap in
            if suggestions:
                items_html = "".join(
                    [
                        f'<div class="px-3 py-2 hover:bg-gray-100 cursor-pointer" '
                        f"onclick=\"selectAutocomplete('{field_name}', '{suggestion}')\">{suggestion}</div>"
                        for suggestion in suggestions[:5]  # Limit to 5 suggestions
                    ],
                )
                return HTMLResponse(
                    content=f'<div class="absolute z-10 bg-white border border-gray-300 rounded-md shadow-lg max-h-40 overflow-y-auto">{items_html}</div>',
                    status_code=200,
                )
            return HTMLResponse(content="", status_code=200)

        except Exception as e:  # noqa: BLE001 — controller boundary; all errors become HTTP 400 responses
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.exception("Autocomplete error for %s", field_name)
            return HTMLResponse(
                content=f'<div class="text-red-500 text-sm">Autocomplete error: {e!s}</div>',
                status_code=400,
            )

    @post("/api/forms/async-validate/{field_name}")
    async def async_validate_field(self, field_name: str, request) -> Any:
        """Handle async validation for fields like username availability."""
        try:
            if request.headers.get("content-type") == "application/json":
                data = await request.json()
            else:
                form_data = await request.form()
                data = dict(form_data)

            field_value = data.get(field_name)

            # Simulate async validation (e.g., checking username availability)
            await asyncio.sleep(0.5)  # Simulate API/database call

            if field_name == "username":
                # Simulate checking if username is taken
                taken_usernames = ["admin", "root", "user", "test"]
                if field_value in taken_usernames:
                    return JSONResponse(
                        {"valid": False, "message": "Username is already taken"},
                    )

            return JSONResponse({"valid": True, "message": "Available"})

        except Exception as e:  # noqa: BLE001 — controller boundary; all errors become HTTP 400 responses
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.exception("Async validation error for %s", field_name)
            return JSONResponse(
                {"valid": False, "message": f"Validation failed: {e!s}"},
                status_code=400,
            )
