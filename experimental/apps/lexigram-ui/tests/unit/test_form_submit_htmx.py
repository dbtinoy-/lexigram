"""Form (organisms) HTMX submission behavior.

The base :class:`~lexigram.ui.organisms.forms.Form` must progressive-enhance
native POST forms: with htmx present the submit is intercepted (``hx-post`` +
``hx-target``), without JavaScript the native action/method POST still works.
No inline ``onclick`` submit JavaScript should ever be emitted.
"""

from __future__ import annotations

from lexigram.ui import Form, render_to_string


class TestFormHTMX:
    def test_post_form_emits_htmx_attrs(self) -> None:
        form = Form(
            action_url="/admin/users/create",
            method="post",
            hx_target="#slide-over-container",
            hx_swap="innerHTML",
        )
        html = render_to_string(form)
        assert 'action="/admin/users/create"' in html
        assert 'method="post"' in html
        assert 'hx-post="/admin/users/create"' in html
        assert 'hx-target="#slide-over-container"' in html
        assert 'hx-swap="innerHTML"' in html
        assert "onclick" not in html

    def test_post_form_emits_indicator_when_set(self) -> None:
        form = Form(
            action_url="/admin/users/create",
            hx_indicator="#submit-status",
        )
        html = render_to_string(form)
        assert 'hx-indicator="#submit-status"' in html

    def test_get_form_emits_htmx_get(self) -> None:
        form = Form(
            action_url="/admin/users?page=2",
            method="get",
            hx_target="#table-data",
            hx_swap="innerHTML",
            submit_label=None,
        )
        html = render_to_string(form)
        assert 'hx-get="/admin/users?page=2"' in html
        assert 'hx-target="#table-data"' in html
        assert 'method="get"' in html
        assert "onclick" not in html

    def test_no_action_renders_plain_form(self) -> None:
        form = Form(action_url=None, submit_label="Save")
        html = render_to_string(form)
        assert "<form" in html
        assert "hx-post" not in html
        assert "onclick" not in html
