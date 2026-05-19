"""Tests for FormValidationController — real-time validation and autocomplete."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.form_validation import FormValidationController
from lexigram.serialization import loads


def _mock_request(
    method: str = "GET",
    form: dict | None = None,
    json_data: dict | None = None,
    headers: dict | None = None,
) -> MagicMock:
    req = MagicMock(spec=Request)
    req.method = method
    req.headers = headers or {}

    async def _form() -> dict:
        return form or {}

    async def _json() -> dict:
        return json_data or {}

    req.form = _form
    req.json = _json
    req.query_params = {"q": ""}
    return req


class TestFormValidationController:
    """Tests for FormValidationController."""

    @pytest.fixture
    def renderer(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def controller(self, renderer: MagicMock) -> FormValidationController:
        return FormValidationController(renderer=renderer)

    # -- validate_field (POST /api/forms/validate/{field_name}) --

    @pytest.mark.asyncio
    async def test_validate_field_clears_on_valid(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request(method="POST", form={"email": "good@test.com"})
        resp = await controller.validate_field("email", req)
        assert resp.status_code == 200
        assert resp.body == b""

    @pytest.mark.asyncio
    async def test_validate_field_returns_error_on_invalid_email(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request(method="POST", form={"email": "not-an-email"})
        resp = await controller.validate_field("email", req)
        assert resp.status_code == 200
        assert b"text-destructive" in resp.body
        assert b"Invalid email address" in resp.body

    @pytest.mark.asyncio
    async def test_validate_field_empty_value(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request(method="POST", form={"email": ""})
        resp = await controller.validate_field("email", req)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_validate_field_unknown_field(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request(method="POST", form={"unknown": "val"})
        resp = await controller.validate_field("unknown", req)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_validate_field_with_json_body(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request(
            method="POST",
            json_data={"email": "bad"},
            headers={"content-type": "application/json"},
        )
        resp = await controller.validate_field("email", req)
        assert resp.status_code == 200
        assert b"Invalid email address" in resp.body

    @pytest.mark.asyncio
    async def test_validate_field_exception_returns_400(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request(method="POST")
        req.form = AsyncMock(side_effect=RuntimeError("boom"))
        resp = await controller.validate_field("email", req)
        assert resp.status_code == 400
        assert b"Validation error" in resp.body

    # -- autocomplete_field (GET /api/forms/autocomplete/{field_name}) --

    @pytest.mark.asyncio
    async def test_autocomplete_country(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request()
        req.query_params = {"q": "uni"}  # matches "United States", "United Kingdom"
        resp = await controller.autocomplete_field("country", req)
        assert resp.status_code == 200
        assert b"United" in resp.body

    @pytest.mark.asyncio
    async def test_autocomplete_city(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request()
        req.query_params = {"q": "lon"}
        resp = await controller.autocomplete_field("city", req)
        assert resp.status_code == 200
        assert b"London" in resp.body

    @pytest.mark.asyncio
    async def test_autocomplete_tags(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request()
        req.query_params = {"q": "urg"}
        resp = await controller.autocomplete_field("tags", req)
        assert resp.status_code == 200
        assert b"urgent" in resp.body

    @pytest.mark.asyncio
    async def test_autocomplete_no_match_returns_empty(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request()
        req.query_params = {"q": "xyznonexistent"}
        resp = await controller.autocomplete_field("country", req)
        assert resp.status_code == 200
        assert resp.body == b""

    @pytest.mark.asyncio
    async def test_autocomplete_case_insensitive(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request()
        req.query_params = {"q": "UNI"}
        resp = await controller.autocomplete_field("country", req)
        assert resp.status_code == 200
        assert b"United" in resp.body

    @pytest.mark.asyncio
    async def test_autocomplete_limits_to_five(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request()
        req.query_params = {"q": ""}
        resp = await controller.autocomplete_field("country", req)
        assert resp.status_code == 200
        # 6 countries exist but filtered to 5
        assert resp.body.count(b"selectAutocomplete") <= 5

    @pytest.mark.asyncio
    async def test_autocomplete_exception_returns_400(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request()

        class _Exploding(dict):
            def get(self, key: str, default: str = "") -> str:  # type: ignore[override]
                raise RuntimeError("boom")

        req.query_params = _Exploding()
        resp = await controller.autocomplete_field("country", req)
        assert resp.status_code == 400
        assert b"Autocomplete error" in resp.body

    # -- async_validate_field (POST /api/forms/async-validate/{field_name}) --

    @pytest.mark.asyncio
    async def test_async_validate_username_taken(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request(method="POST", form={"username": "admin"})
        resp = await controller.async_validate_field("username", req)
        assert resp.status_code == 200
        body = loads(resp.body)
        assert body["valid"] is False
        assert "already taken" in body["message"]

    @pytest.mark.asyncio
    async def test_async_validate_username_available(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request(method="POST", form={"username": "newuser42"})
        resp = await controller.async_validate_field("username", req)
        assert resp.status_code == 200
        body = loads(resp.body)
        assert body["valid"] is True
        assert body["message"] == "Available"

    @pytest.mark.asyncio
    async def test_async_validate_unknown_field(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request(method="POST", form={"color": "blue"})
        resp = await controller.async_validate_field("color", req)
        assert resp.status_code == 200
        body = loads(resp.body)
        assert body["valid"] is True

    @pytest.mark.asyncio
    async def test_async_validate_with_json_body(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request(
            method="POST",
            json_data={"username": "root"},
            headers={"content-type": "application/json"},
        )
        resp = await controller.async_validate_field("username", req)
        assert resp.status_code == 200
        body = loads(resp.body)
        assert body["valid"] is False

    @pytest.mark.asyncio
    async def test_async_validate_exception_returns_400(
        self, controller: FormValidationController
    ) -> None:
        req = _mock_request(method="POST")
        req.form = AsyncMock(side_effect=RuntimeError("boom"))
        resp = await controller.async_validate_field("username", req)
        assert resp.status_code == 400
        body = loads(resp.body)
        assert body["valid"] is False
        assert "Validation failed" in body["message"]
