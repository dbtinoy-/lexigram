"""Hostile-value rendering tests for BelongsToManyRelationManager (F2 stored XSS)."""

from __future__ import annotations

import re
from html import unescape
from types import SimpleNamespace
from typing import Any

import pytest

from lexigram.admin.relations import BelongsToManyRelationManager
from lexigram.serialization import loads_str


def _item(id: str, name: str = "Rex") -> Any:
    return type("Item", (), {"id": id, "name": name})()


def _extract_hx_vals(html: str) -> dict[str, Any]:
    match = re.search(r'hx-vals="([^"]*)"', html)
    assert match is not None, "hx-vals attribute not found in output"
    return loads_str(unescape(match.group(1)))


HOSTILE_ID = 'x" onmouseover="alert(1)<img src=x onerror=alert(1)>'


class _HostileBelongsToMany(BelongsToManyRelationManager):
    relationship_name = "roles"
    pivot_table = "user_roles"
    pivot_columns = ["assigned_at", "is_primary"]
    related_key = "role_id"
    related_key_local = "user_id"

    async def get_query(self) -> list[Any]:
        return [_item(HOSTILE_ID, "<img src=x onerror=alert(1)>")]

    async def get_attached_ids(self) -> list[str]:
        return [HOSTILE_ID]

    async def get_pivot_data(self, related_id: str) -> dict[str, Any] | None:
        return {"assigned_at": '" autofocus onfocus="alert(1)', "is_primary": "true"}


class _BenignBelongsToMany(_HostileBelongsToMany):
    async def get_query(self) -> list[Any]:
        return [_item("1", "Admin")]

    async def get_attached_ids(self) -> list[str]:
        return ["1"]

    async def get_pivot_data(self, related_id: str) -> dict[str, Any] | None:
        return {"assigned_at": "2026-01-01", "is_primary": "true"}


class TestBelongsToManyRenderXss:
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_render_uses_request_admin_prefix(self) -> None:
        mgr = _BenignBelongsToMany(parent_id="parent-1")
        request = SimpleNamespace(scope={"admin_prefix": "/backoffice"})

        html = await mgr.render(request=request, resource_name="users")

        assert "/backoffice/users/parent-1/relations/roles/toggle" in html
        assert "/admin/users/parent-1/relations/roles/toggle" not in html

    @pytest.mark.asyncio
    async def test_hostile_label_escaped_in_cell_text(self) -> None:
        mgr = _HostileBelongsToMany(parent_id="parent-1")
        html = await mgr.render(request=None, resource_name="users")
        assert "&lt;img" in html
        assert "<img" not in html

    @pytest.mark.asyncio
    async def test_hostile_item_id_escaped_in_attributes(self) -> None:
        mgr = _HostileBelongsToMany(parent_id="parent-1")
        html = await mgr.render(request=None, resource_name="users")
        assert 'data-related-id="x&quot; onmouseover=&quot;alert(1)' in html
        assert "&lt;img" in html
        assert "<img" not in html
        assert '<img ' not in html

    @pytest.mark.asyncio
    async def test_hostile_pivot_value_escaped_in_value_attribute(self) -> None:
        mgr = _HostileBelongsToMany(parent_id="parent-1")
        html = await mgr.render(request=None, resource_name="users")
        assert 'value="&quot; autofocus onfocus=&quot;alert(1)' in html
        assert 'autofocus="' not in html
        assert 'onfocus="' not in html

    @pytest.mark.asyncio
    async def test_hx_vals_round_trips_to_exact_dict(self) -> None:
        mgr = _HostileBelongsToMany(parent_id="parent-1")
        html = await mgr.render(request=None, resource_name="users")
        assert _extract_hx_vals(html) == {"related_id": HOSTILE_ID}

    @pytest.mark.asyncio
    async def test_single_row_refresh_escapes_ids_and_round_trips(self) -> None:
        mgr = _HostileBelongsToMany(parent_id="parent-1")
        response = await mgr._render_single_row(
            request=None,
            resource_name="users",
            related_id=HOSTILE_ID,
        )
        body = response.body.decode()
        assert "&lt;img" in body
        assert "<img" not in body
        assert 'data-related-id="x&quot; onmouseover=&quot;alert(1)' in body
        assert _extract_hx_vals(body) == {"related_id": HOSTILE_ID}

    @pytest.mark.asyncio
    async def test_benign_hx_vals_round_trips_to_plain_id(self) -> None:
        mgr = _BenignBelongsToMany(parent_id="parent-1")
        html = await mgr.render(request=None, resource_name="users")
        assert _extract_hx_vals(html) == {"related_id": "1"}