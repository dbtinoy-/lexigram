"""SlideOver form action-bar contract.

A panel embedding a form must never render two submit buttons, and any
footer Save must actually submit the form it appears next to. Regression
coverage for the "1 cancel + 2 save buttons in the table form side panel"
defect (duplicate in-form submit + dead footer Save with no ``form``).
"""

from __future__ import annotations

import re

from lexigram.ui import el, render_to_string
from lexigram.ui.organisms.forms import Form
from lexigram.ui.organisms.slide_over import SlideOver

_BUTTON_RE = re.compile(r"<button[^>]*>.*?</button>", re.S)


def _submits(html: str) -> list[str]:
    return [b for b in _BUTTON_RE.findall(html) if 'type="submit"' in b]


class TestSlideOverFormActions:
    def test_suppressing_form_moves_actions_to_footer_bound_via_form_attr(
        self,
    ) -> None:
        form = Form(
            action_url="/admin/users/create",
            form_id="users-create-form",
            submit_label="Create user",
            suppress_submit=True,
            hx_target="#slide-over-container",
        )
        html = render_to_string(
            SlideOver(
                title="Create User",
                trigger=None,
                render_trigger=False,
                is_open=True,
                children=[form],
            ),
        )

        submits = _submits(html)
        # Exactly one submit, located in the footer and bound to the form.
        assert len(submits) == 1
        assert 'form="users-create-form"' in submits[0]
        assert 'id="users-create-form"' in html
        assert "Cancel" in html
        # No in-form action row remains inside the <form>.
        form_markup = re.search(
            r"<form.*?</form>",
            html,
            re.S,
        )
        assert form_markup is not None
        assert 'type="submit"' not in form_markup.group(0)

    def test_non_suppressing_form_keeps_its_own_submit_and_no_footer(
        self,
    ) -> None:
        form = Form(
            action_url="/admin/users/create",
            form_id="users-create-form",
            submit_label="Create user",
            suppress_submit=False,
        )
        html = render_to_string(
            SlideOver(
                title="Create User",
                trigger=None,
                render_trigger=False,
                is_open=True,
                children=[form],
            ),
        )

        submits = _submits(html)
        assert len(submits) == 1
        # Submit stays inside the form; no dead footer duplicate.
        assert "Cancel" not in html
        assert 'form="users-create-form"' not in html

    def test_nested_form_with_own_submit_gets_no_footer_duplicate(self) -> None:
        form = Form(
            action_url="/admin/users/create",
            form_id="users-create-form",
            submit_label="Save",
            suppress_submit=False,
        )
        html = render_to_string(
            SlideOver(
                title="Edit",
                trigger=None,
                render_trigger=False,
                is_open=True,
                children=[el("div", form)],
            ),
        )
        assert len(_submits(html)) == 1

    def test_raw_form_without_id_gets_bound_footer(self) -> None:
        html = render_to_string(
            SlideOver(
                title="Customize",
                trigger=None,
                render_trigger=False,
                is_open=True,
                children=[
                    el(
                        "form",
                        el("input", name="title", type_="text"),
                        method="post",
                        action="/admin/widgets/save",
                    ),
                ],
            ),
        )
        submits = _submits(html)
        assert len(submits) == 1
        assert 'form="slide-over-form"' in submits[0]
        assert 'id="slide-over-form"' in html
        assert "Cancel" in html
