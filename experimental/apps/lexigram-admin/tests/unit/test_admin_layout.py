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


class TestAdminLayoutBody:
    """Tests for AdminLayout.render_body_content().

    This method had no coverage, which is how a bare ``asset_prefix``
    reference survived: it is a local of ``render_head_content``, so every
    call here raised NameError once execution reached the admin.js tag.
    """

    def _layout(self, base_url: str = "/admin") -> AdminLayout:
        return AdminLayout(
            config=AdminLayoutConfig(),
            context=AdminLayoutContext(base_url=base_url),
        )

    def test_render_body_content_does_not_raise(self) -> None:
        assert self._layout().render_body_content("<p>hi</p>")

    def test_admin_js_is_included(self) -> None:
        body = self._layout().render_body_content()

        assert "/static/js/admin.js" in body

    def test_admin_js_uses_the_context_base_url(self) -> None:
        """The prefix must follow the mount point, not a hardcoded /admin."""
        body = self._layout(base_url="/backoffice").render_body_content()

        assert 'src="/backoffice/static/js/admin.js"' in body

    def test_trailing_slash_is_normalised(self) -> None:
        body = self._layout(base_url="/admin/").render_body_content()

        assert 'src="/admin/static/js/admin.js"' in body

    def test_empty_base_url_falls_back_to_admin(self) -> None:
        body = self._layout(base_url="").render_body_content()

        assert 'src="/admin/static/js/admin.js"' in body
