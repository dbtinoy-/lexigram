"""Tests for admin layout rendering."""

from __future__ import annotations

from lexigram.admin.ui.layouts.admin_layout import (
    AdminLayout,
    AdminLayoutConfig,
    AdminLayoutContext,
)


class TestAdminLayoutHead:
    """Tests for AdminLayout.render_head_content()."""

    def test_sortablejs_cdn_included(self) -> None:
        """Verify SortableJS CDN script tag is in head content."""
        layout = AdminLayout(
            config=AdminLayoutConfig(),
            context=AdminLayoutContext(),
        )
        head = layout.render_head_content()
        assert 'src="https://unpkg.com/sortablejs@1.15.0/Sortable.min.js"' in head
