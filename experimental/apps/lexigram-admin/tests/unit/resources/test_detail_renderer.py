from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from pydantic import BaseModel
import pytest

from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.resources.detail_renderer import DetailRenderer


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
    resource = SimpleNamespace(service=_FakeService(item), model=None)

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
