from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from pydantic import BaseModel
import pytest
from starlette.requests import Request

from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.resources.detail_renderer import DetailRenderer
from lexigram.admin.schema import TextField


class _Model(BaseModel):
    name: str
    active: bool
    since: date
    website: str
    price: float


class _FakeService:
    def __init__(self, item):
        self._item = item

    async def get(self, item_id: str) -> _Model:
        return self._item


def _renderer() -> DetailRenderer:
    return DetailRenderer(
        config=SimpleNamespace(prefix="/admin"),
        resource_name="widgets",
        renderer=AdminRenderer(None),
    )


def _fragment_request(path: str = "/admin/widgets/1") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [(b"hx-target", b"#content")],
            "client": ("test", 1),
            "server": ("test", 80),
            "scheme": "http",
            "root_path": "",
            "state": {},
            "admin_prefix": "/admin",
        }
    )


@pytest.mark.asyncio
async def test_detail_renders_infolist_widget() -> None:
    item = _Model(
        name="Acme",
        active=True,
        since=date(2026, 5, 28),
        website="https://example.com",
        price=12.5,
    )
    renderer = _renderer()
    resource = SimpleNamespace(service=_FakeService(item), model=_Model)

    html = await renderer._get_item_html(resource, "w-1", "Widget")

    assert "Item not found" not in html
    assert "Acme" in html
    assert "\u2713 Yes" in html
    assert "2026-05-28" in html


@pytest.mark.asyncio
async def test_detail_render_missing_item() -> None:
    class EmptyService:
        async def get(self, item_id: str):
            return None

    renderer = _renderer()
    resource = SimpleNamespace(service=EmptyService(), model=_Model)

    html = await renderer._get_item_html(resource, "w-1", "Widget")

    assert "Item not found" in html


@pytest.mark.asyncio
async def test_detail_falls_back_to_table_without_model() -> None:
    item = SimpleNamespace(model_dump=lambda: {"name": "Acme"})
    renderer = _renderer()
    resource = SimpleNamespace(
        service=_FakeService(item),
        model=None,
        fields=[TextField(name="name")],
    )

    html = await renderer._get_item_html(resource, "w-1", "Widget")

    assert "<table" in html
    assert "Acme" in html


@pytest.mark.asyncio
async def test_detail_falls_back_without_service() -> None:
    """A resource with no data access reports not-found instead of a placeholder."""
    renderer = _renderer()
    resource = SimpleNamespace(service=None, model=_Model)

    html = await renderer._get_item_html(resource, "w-1", "Widget")

    assert "Item not found" in html


@pytest.mark.asyncio
async def test_detail_hides_edit_action_without_update_permission() -> None:
    item = _Model(
        name="Acme",
        active=True,
        since=date(2026, 5, 28),
        website="https://example.com",
        price=12.5,
    )

    class ReadOnlyResource(SimpleNamespace):
        def has_change_permission(self, user: object) -> bool:
            return False

    resource = ReadOnlyResource(service=_FakeService(item), model=_Model)
    html = (
        await _renderer().render_detail(_fragment_request(), resource, "1")
    ).body.decode()

    assert "Edit" not in html


@pytest.mark.asyncio
async def test_detail_escapes_untrusted_record_id_in_fragment() -> None:
    item = _Model(
        name="Acme",
        active=True,
        since=date(2026, 5, 28),
        website="https://example.com",
        price=12.5,
    )
    renderer = _renderer()
    resource = SimpleNamespace(service=_FakeService(item), model=_Model)

    html = (
        await renderer.render_detail(
            _fragment_request(), resource, '1"><script>alert(1)</script>'
        )
    ).body.decode()

    assert '<script>alert(1)</script>' not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


@pytest.mark.asyncio
async def test_inline_detail_only_renders_declared_view_fields() -> None:
    class InlineModel(BaseModel):
        name: str

    class InlineSource:
        async def find_one(self, item_id: str) -> dict[str, str]:
            return {"name": "Acme", "secret": "do-not-render"}

    resource = SimpleNamespace(
        model=InlineModel,
        fields=[TextField(name="name")],
        _data_source=InlineSource(),
        form_exclude_fields=(),
    )
    renderer = _renderer()

    html = (
        await renderer.render_inline_edit(_fragment_request(), resource, "1")
    ).body.decode()

    assert "Acme" in html
    assert "do-not-render" not in html
    assert "secret" not in html
