"""BelongsTo option population in generated resource forms.

Relation options must load through the canonical ``IDataSource.find_many``
interface (the old ``list_all`` call never existed on the protocol, so
relation dropdowns silently stayed empty).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from starlette.requests import Request as StarletteRequest

from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.form_renderer import FormRenderer


class _Widget(BaseModel):
    name: str
    owner_id: int


class _OwnerRecord:
    def __init__(self, pk: int, label: str) -> None:
        self.id = pk
        self.label = label

    def __str__(self) -> str:
        return self.label


class _RelatedDataSource:
    """Minimal IDataSource compliant stub (find_many only)."""

    def __init__(self, records: list[_OwnerRecord]) -> None:
        self._records = records

    async def find_many(self, query: object) -> object:
        return SimpleNamespace(items=self._records)


class _RelatedResource(Resource):
    name = "owners"
    _data_source = _RelatedDataSource(
        [_OwnerRecord(1, "Ada"), _OwnerRecord(2, "Grace")]
    )


class _OwnerResource(Resource):
    name = "widgets"
    model = _Widget
    _admin_registry = {"owners": _RelatedResource}


def _create_request() -> StarletteRequest:
    scope: dict = {
        "type": "http",
        "method": "GET",
        "path": "/admin/widgets/create",
        "raw_path": b"/admin/widgets/create",
        "query_string": b"",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "path_params": {},
        "state": MagicMock(),
        "app": None,
        "session": {},
    }
    return StarletteRequest(scope)


class TestBelongsToOptions:
    @pytest.mark.asyncio
    async def test_options_populate_from_find_many(self) -> None:
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "widgets",
            AdminRenderer(),
        )
        response = await renderer.render_create(_create_request(), _OwnerResource)
        html = response.body.decode("utf-8", "replace")
        assert 'name="owner_id"' in html
        assert 'value="1"' in html
        assert "Ada" in html
        assert 'value="2"' in html
        assert "Grace" in html

    @pytest.mark.asyncio
    async def test_options_load_uses_query_spec(self) -> None:
        captured: list[object] = []

        class _SpyDataSource(_RelatedDataSource):
            async def find_many(self, query: object) -> object:
                captured.append(query)
                return await super().find_many(query)

        class _RelatedResourceSpy(Resource):
            name = "owners"
            _data_source = _SpyDataSource(
                [_OwnerRecord(1, "Ada"), _OwnerRecord(2, "Grace")]
            )

        class _OwnerResourceSpy(Resource):
            name = "widgets"
            model = _Widget
            _admin_registry = {"owners": _RelatedResourceSpy}

        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "widgets",
            AdminRenderer(),
        )
        await renderer.render_create(_create_request(), _OwnerResourceSpy)
        assert len(captured) == 1
        query = captured[0]
        assert getattr(query, "per_page", None) == 200
        assert getattr(query, "sort_by", None) == "id"

    @pytest.mark.asyncio
    async def test_form_submits_via_htmx_to_slide_over(self) -> None:
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "widgets",
            AdminRenderer(),
        )
        response = await renderer.render_create(_create_request(), _OwnerResource)
        html = response.body.decode("utf-8", "replace")
        assert 'hx-post="/admin/widgets/create"' in html
        assert 'hx-target="#slide-over-container"' in html
        # No JS onclick form submit — htmx intercepts, native POST is fallback.
        assert "f.submit()" not in html
