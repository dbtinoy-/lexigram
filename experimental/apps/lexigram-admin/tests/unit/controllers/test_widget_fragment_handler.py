"""render_widget_fragment end-to-end (contributor → ChartContent → HTML).

The widget-fragment handler is the HTMX dashboard's live path: it resolves
the contributor, applies permission + config, calls render_widget, and wraps
the resulting WidgetContent.  Charts must survive that whole flow (not just
wrap_widget_body in isolation).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.controllers.widget_content_handlers import (
    render_widget_fragment,
)
from lexigram.contracts.admin.types import WidgetViewModel
from lexigram.contracts.admin.widget_content import ChartContent, ChartPoint
from lexigram.result import Ok


def _make_request() -> MagicMock:
    request = MagicMock()
    request.query_params = {}
    return request


class _WidgetDef:
    def __init__(self, name: str, permission: str | None) -> None:
        self.name = name
        self.permission = permission


@pytest.mark.asyncio
async def test_chart_widget_renders_through_fragment_handler() -> None:
    registry = MagicMock()
    contributor = MagicMock()
    contributor.name = "infra"
    contributor.get_dashboard_widgets.return_value = [
        _WidgetDef("pulse", None)
    ]
    contributor.render_widget = AsyncMock(
        return_value=Ok(
            WidgetViewModel(
                content=ChartContent(
                    chart_type="bar",
                    points=(
                        ChartPoint(label="users", value=3),
                        ChartPoint(label="roles", value=2),
                    ),
                ),
                title="Resources",
            )
        )
    )
    registry.get.return_value = contributor

    response = await render_widget_fragment(
        _make_request(),
        contributor_id="infra",
        widget_name="pulse",
        registry=registry,
        settings_service=None,
        resolver=None,
        resolve_tenant=AsyncMock(return_value="default"),
        has_permission=lambda _req, _perm: True,
    )
    body = response.body
    assert b"Resources" in body
    assert b"users" in body
    assert b"roles" in body
    assert b'role="img"' in body
    assert b"widget-error-card" not in body
    assert b"widget-content" in body


@pytest.mark.asyncio
async def test_widget_def_permission_blocks_render() -> None:
    registry = MagicMock()
    contributor = MagicMock()
    contributor.get_dashboard_widgets.return_value = [
        _WidgetDef("secret", "widget.secret")
    ]
    registry.get.return_value = contributor

    response = await render_widget_fragment(
        _make_request(),
        contributor_id="infra",
        widget_name="secret",
        registry=registry,
        settings_service=None,
        resolver=None,
        resolve_tenant=AsyncMock(return_value="default"),
        has_permission=lambda _req, _perm: False,
    )
    assert b"widget-error-card" in response.body
    assert b"permission" in response.body
    contributor.render_widget.assert_not_called()
