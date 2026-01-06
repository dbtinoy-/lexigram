"""Tests for DraftController — form auto-save and retrieval."""

from __future__ import annotations

# DraftController imports from lexigram.admin.services.forms.draft_service which
# does not exist yet. Create a stub module so the import resolves.
import types as _types
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

_draft_stub = _types.ModuleType("lexigram.admin.services.forms.draft_service")


class _StubDraftService:
    def save_draft(self, form_id: str, user_id: str, data: dict) -> None: ...

    def get_draft(self, form_id: str, user_id: str) -> None: ...


_draft_stub.DraftService = _StubDraftService

_form_module = _types.ModuleType("lexigram.admin.services.forms")
_form_module.draft_service = _draft_stub
_draft_stub.__package__ = "lexigram.admin.services.forms"

_built: dict[str, object] = {}


def _setup() -> None:
    import sys

    _built.clear()
    sys.modules["lexigram.admin.services.forms"] = _form_module
    sys.modules["lexigram.admin.services.forms.draft_service"] = _draft_stub

    from lexigram.admin.controllers.draft_controller import DraftController

    _built["DraftController"] = DraftController


def _teardown() -> None:
    import sys

    sys.modules.pop("lexigram.admin.services.forms", None)
    sys.modules.pop("lexigram.admin.services.forms.draft_service", None)
    _built.clear()


def _mock_request(
    method: str = "GET",
    form_data: dict | None = None,
    json_data: dict | None = None,
    headers: dict | None = None,
) -> MagicMock:
    req = MagicMock(spec=Request)
    req.method = method
    req.headers = headers or {}
    req.state = MagicMock()
    req.state.user = MagicMock()
    req.state.user.user_id = "user-123"

    async def _form() -> dict:
        return form_data or {}

    async def _json() -> dict:
        return json_data or {}

    req.form = _form
    req.json = _json
    return req


class TestDraftController:
    """Tests for DraftController."""

    @pytest.fixture(autouse=True)
    def _patch_imports(self) -> None:
        _setup()
        yield
        _teardown()

    @pytest.fixture
    def renderer(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def draft_service(self) -> AsyncMock:
        svc = AsyncMock()
        svc.save_draft = AsyncMock(return_value=None)
        svc.get_draft = AsyncMock(return_value=None)
        return svc

    @pytest.fixture
    def controller(self, renderer: MagicMock, draft_service: AsyncMock) -> object:
        DraftController = _built["DraftController"]
        return DraftController(renderer=renderer, draft_service=draft_service)

    # -- save_draft (POST /api/forms/draft/{form_id}) --

    @pytest.mark.asyncio
    async def test_save_draft_saves_form_data(
        self, controller: object, draft_service: AsyncMock
    ) -> None:
        req = _mock_request(
            method="POST", form_data={"title": "Hello", "body": "World"}
        )
        resp = await controller.save_draft("form-1", req)
        assert resp.status_code == 200
        draft_service.save_draft.assert_awaited_once_with(
            "form-1", "user-123", {"title": "Hello", "body": "World"}
        )

    @pytest.mark.asyncio
    async def test_save_draft_strips_sensitive_fields(
        self, controller: object, draft_service: AsyncMock
    ) -> None:
        req = _mock_request(
            method="POST",
            form_data={"csrf_token": "secret", "password": "p@ss", "title": "Safe"},
        )
        resp = await controller.save_draft("form-1", req)
        assert resp.status_code == 200
        draft_service.save_draft.assert_awaited_once_with(
            "form-1", "user-123", {"title": "Safe"}
        )

    @pytest.mark.asyncio
    async def test_save_draft_with_json_body(
        self, controller: object, draft_service: AsyncMock
    ) -> None:
        req = _mock_request(
            method="POST",
            json_data={"title": "JSON draft"},
            headers={"content-type": "application/json"},
        )
        resp = await controller.save_draft("form-1", req)
        assert resp.status_code == 200
        draft_service.save_draft.assert_awaited_once_with(
            "form-1", "user-123", {"title": "JSON draft"}
        )

    @pytest.mark.asyncio
    async def test_save_draft_anonymous_user(
        self, controller: object, draft_service: AsyncMock
    ) -> None:
        req = _mock_request(method="POST", form_data={"title": "Anon"})
        req.state.user = None
        resp = await controller.save_draft("form-1", req)
        assert resp.status_code == 200
        draft_service.save_draft.assert_awaited_once_with(
            "form-1", "anonymous", {"title": "Anon"}
        )

    @pytest.mark.asyncio
    async def test_save_draft_exception_returns_500(
        self, controller: object, draft_service: AsyncMock
    ) -> None:
        draft_service.save_draft.side_effect = RuntimeError("boom")
        req = _mock_request(method="POST", form_data={"title": "Fail"})
        resp = await controller.save_draft("form-1", req)
        assert resp.status_code == 500
        assert b"Autosave failed" in resp.body

    # -- get_draft (GET /api/forms/draft/{form_id}) --

    @pytest.mark.asyncio
    async def test_get_draft_returns_draft_data(
        self, controller: object, draft_service: AsyncMock
    ) -> None:
        draft = MagicMock()
        draft.data = {"title": "Saved"}
        draft.updated_at.isoformat.return_value = "2026-05-25T12:00:00"
        draft_service.get_draft.return_value = draft

        req = _mock_request()
        resp = await controller.get_draft("form-1", req)
        assert resp.status_code == 200
        from lexigram.serialization import loads as _loads

        body = _loads(resp.body)
        assert body["status"] == "success"
        assert body["data"] == {"title": "Saved"}

    @pytest.mark.asyncio
    async def test_get_draft_not_found(
        self, controller: object, draft_service: AsyncMock
    ) -> None:
        draft_service.get_draft.return_value = None
        req = _mock_request()
        resp = await controller.get_draft("form-1", req)
        assert resp.status_code == 404
        from lexigram.serialization import loads as _loads

        body = _loads(resp.body)
        assert body["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_draft_anonymous(
        self, controller: object, draft_service: AsyncMock
    ) -> None:
        req = _mock_request()
        req.state.user = None
        resp = await controller.get_draft("form-1", req)
        assert resp.status_code == 404
        draft_service.get_draft.assert_awaited_once_with("form-1", "anonymous")

    @pytest.mark.asyncio
    async def test_get_draft_exception_returns_500(
        self, controller: object, draft_service: AsyncMock
    ) -> None:
        draft_service.get_draft.side_effect = RuntimeError("boom")
        req = _mock_request()
        resp = await controller.get_draft("form-1", req)
        assert resp.status_code == 500
        from lexigram.serialization import loads as _loads

        body = _loads(resp.body)
        assert body["status"] == "error"
