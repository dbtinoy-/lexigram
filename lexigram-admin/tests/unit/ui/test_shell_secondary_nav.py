"""Tests for shell layout stability and the cluster content layout.

The shell keeps ``#main-content`` classes constant so HTMX swaps between
pages (e.g. Infrastructure -> Settings) never inherit a leftover flex
wrapper; cluster centers render their secondary sidebar inside their own
content via ``ClusterLayout``.
"""

from __future__ import annotations

from lexigram.admin.ui.organisms.secondary_nav import ClusterLayout
from lexigram.admin.ui.templates.shell import AdminShell
from lexigram.ui import el, raw, render_to_string


def test_main_content_has_constant_classes() -> None:
    shell = AdminShell(content="<div>page-body</div>")
    html = render_to_string(shell)
    main_section = html.split('id="main-content"')[1].split("</main>")[0]
    assert "px-4 py-4" in main_section
    assert "lg:flex-row" not in main_section


def test_shell_omits_secondary_nav_markup() -> None:
    shell = AdminShell(content="<div/>")
    html = render_to_string(shell)
    assert "Secondary navigation" not in html
    assert "/admin/web" not in html


def test_cluster_layout_renders_sidebar_next_to_content() -> None:
    secondary = [
        {
            "label": "Web",
            "href": "/admin/web",
            "icon": "globe",
            "active": False,
            "children": [
                {
                    "label": "Routes",
                    "href": "/admin/web/routes",
                    "icon": "map",
                    "active": True,
                },
            ],
        },
        {"label": "Cache", "href": "/admin/cache", "icon": "zap", "active": False},
    ]
    html = render_to_string(
        ClusterLayout(items=secondary, content=el("div", "page-body"))
    )
    assert 'class="flex flex-col lg:flex-row gap-6"' in html
    assert "flex-1 min-w-0" in html
    assert "page-body" in html
    assert "/admin/web" in html
    assert "/admin/web/routes" in html
    assert "/admin/cache" in html


def test_cluster_layout_accepts_raw_html_content() -> None:
    html = render_to_string(
        ClusterLayout(
            items=[{"label": "Web", "href": "/admin/web", "active": False}],
            content=raw("<div>raw-body</div>"),
        )
    )
    assert "raw-body" in html
    assert "<div>raw-body</div>" in html
