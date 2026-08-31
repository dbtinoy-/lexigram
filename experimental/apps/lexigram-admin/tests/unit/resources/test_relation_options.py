"""Relation-options coverage: registry resolution, pluralized names, and
the searchable-select endpoint.

Generated forms resolve related resources from the mounted resource
register (never from a resource-private ``_admin_registry``), so options
keep working for irregular plural names and for resources wired at mount
time through the router.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from pydantic import BaseModel
import pytest
from starlette.requests import Request as StarletteRequest

from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.forms.schema_generator import FormSchemaGenerator
from lexigram.admin.resources.action_handlers import RelationOptionsActionHandler
from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.form_renderer import FormRenderer
from lexigram.admin.schema import BelongsToField
from lexigram.ui import render_to_string


class _Widget(BaseModel):
    name: str
    category_id: int
    tags: list[_Category] | None = None


class _Category(BaseModel):
    label: str


class _CategoryRecord:
    def __init__(self, pk: int, label: str) -> None:
        self.id = pk
        self.label = label

    def __str__(self) -> str:
        return self.label


class _CategoryDataSource:
    def __init__(self, records: list[_CategoryRecord]) -> None:
        self._records = records

    async def find_many(self, query: object) -> object:
        return SimpleNamespace(items=self._records)


class _CategoryResource(Resource):
    name = "categories"
    _data_source = _CategoryDataSource(
        [_CategoryRecord(1, "Tech"), _CategoryRecord(2, "Design")]
    )


class _WidgetResource(Resource):
    name = "widgets"
    model = _Widget


def _renderer(resources: dict[str, object] | None = None) -> FormRenderer:
    return FormRenderer(
        AdminConfig(prefix="/admin", title="Test"),
        "widgets",
        AdminRenderer(),
        resources=resources or {},
    )


def _request(path: str = "/admin/widgets/create", query: str = "") -> StarletteRequest:
    scope: dict = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
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


class TestRelationNameResolution:
    def test_irregular_plural_resolves_from_registry(self) -> None:
        gen = FormSchemaGenerator(resource_registry={"categories": _Category})
        schema = gen.from_pydantic(_Widget)
        field = schema.get_field("category_id")
        assert field.resource == "categories"

    def test_naive_plural_fallback_without_registry(self) -> None:
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(_Widget)
        field = schema.get_field("category_id")
        assert field.resource == "categorys"


class TestGeneratedFormRelationOptions:
    @pytest.mark.asyncio
    async def test_options_populate_from_mounted_resources(self) -> None:
        renderer = _renderer({"categories": _CategoryResource})
        response = await renderer.render_create(_request(), _WidgetResource)
        html = response.body.decode("utf-8", "replace")
        assert 'name="category_id"' in html
        assert "Tech" in html
        assert "Design" in html

    @pytest.mark.asyncio
    async def test_has_many_options_populate(self) -> None:
        renderer = _renderer({"categories": _CategoryResource})
        response = await renderer.render_create(_request(), _WidgetResource)
        html = response.body.decode("utf-8", "replace")
        assert 'name="tags"' in html
        assert "Tech" in html

    def test_searchable_relation_gets_options_url(self) -> None:
        renderer = _renderer({"categories": _CategoryResource})
        field = BelongsToField(
            name="category_id",
            resource="categories",
            searchable=True,
            label="Category",
        )
        component = renderer._create_field_component(field, 1)
        html = render_to_string(component.render())
        assert (
            'hx-get="/admin/categories/relation-options?source=widgets&amp;field=category_id"'
            in html
        )
        assert 'hx-trigger="keyup changed delay:300ms"' in html

    def test_non_searchable_relation_gets_no_options_url(self) -> None:
        renderer = _renderer({"categories": _CategoryResource})
        field = BelongsToField(
            name="category_id", resource="categories", label="Category"
        )
        component = renderer._create_field_component(field, 1)
        html = render_to_string(component.render())
        assert "relation-options" not in html


class TestRelationOptionsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_option_markup(self) -> None:
        handler = RelationOptionsActionHandler(
            resources={"categories": _CategoryResource}
        )
        response = await handler.handle(
            _request("/admin/categories/relation-options"),
            _CategoryResource(),
        )
        assert response.body.decode() == (
            '<option value="1">Tech</option><option value="2">Design</option>'
        )

    @pytest.mark.asyncio
    async def test_filters_by_query_and_escapes(self) -> None:
        class _EvilRecord(_CategoryRecord):
            def __str__(self) -> str:
                return "<script>alert(1)</script>"

        class _EvilResource(_CategoryResource):
            _data_source = _CategoryDataSource([_EvilRecord(7, "")])

        handler = RelationOptionsActionHandler(resources={"categories": _EvilResource})
        response = await handler.handle(
            _request("/admin/categories/relation-options", "q=script"),
            _EvilResource(),
        )
        assert "&lt;script&gt;" in response.body.decode()
        assert "<script>" not in response.body.decode()

    @pytest.mark.asyncio
    async def test_source_field_permission_is_enforced(self) -> None:
        class _DenyFieldPermissions:
            async def can_view_field(
                self, user: object, resource: str, field: str
            ) -> bool:
                return False

        request = _request(
            "/admin/categories/relation-options",
            "source=widgets&field=category_id",
        )
        request.scope["state"] = {"user": object()}
        request.scope["app"] = SimpleNamespace(
            state=SimpleNamespace(permission_service=_DenyFieldPermissions())
        )
        handler = RelationOptionsActionHandler(
            resources={"categories": _CategoryResource}
        )

        response = await handler.handle(request, _CategoryResource())

        assert response.status_code == 403
        assert response.body == b"Forbidden"

    @pytest.mark.asyncio
    async def test_data_source_failure_returns_service_unavailable(self) -> None:
        class _BrokenDataSource:
            async def find_many(self, query: object) -> object:
                raise RuntimeError("database unavailable")

        class _BrokenResource(_CategoryResource):
            _data_source = _BrokenDataSource()

        handler = RelationOptionsActionHandler(
            resources={"categories": _BrokenResource}
        )
        response = await handler.handle(
            _request("/admin/categories/relation-options"), _BrokenResource()
        )
        assert response.status_code == 503
        assert response.body == b""

    @pytest.mark.asyncio
    async def test_missing_resource_returns_404(self) -> None:
        handler = RelationOptionsActionHandler(resources={})
        response = await handler.handle(
            _request("/admin/categories/relation-options"), None
        )
        assert response.status_code == 404
