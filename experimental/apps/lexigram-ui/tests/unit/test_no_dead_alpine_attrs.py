"""Regression guards for the dead-Alpine-attribute class (B13).

``el()`` converts kwarg underscores to hyphens, so ``x_on_click=...``
renders as ``x-on-click`` — an attribute Alpine.js silently ignores
(Alpine only binds the canonical ``x-on:event`` / ``@event`` forms).
This shipped several completely dead interactions (slide-over close
buttons, modal triggers, section collapse, toggles, builder/query-builder
actions, button loading states).

The htmx equivalent (``hx_on_click`` -> ``hx-on-click``) is *valid*:
htmx explicitly supports the all-dash ``hx-on-`` alias, so only Alpine
``x_on_*`` usage is banned.

Fix pattern: pass a dict attribute with the canonical name, e.g.::

    el("button", {"x-on:click": "open = false"}, ...)
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "lexigram" / "ui"

# Matches `x_on_foo=` kwargs and `"x_on_foo"` dict keys, but not the htmx
# `hx_on_*` alias (valid) and not prose in comments/docstrings.
_DEAD_ALPINE = re.compile(r"""(?<![a-z_])x_on_[a-z_]+\s*=|["']x_on_[a-z_]+["']""")


def test_no_dead_alpine_event_attributes_in_source() -> None:
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _DEAD_ALPINE.search(line):
                offenders.append(f"{path.relative_to(SRC)}:{lineno}: {stripped}")

    assert not offenders, (
        "Alpine `x_on_*` kwargs render as dead `x-on-*` attributes "
        "(Alpine only binds `x-on:event`). Use a dict attribute with the "
        'canonical name instead, e.g. el("button", {"x-on:click": "..."}). '
        "Offending lines:\n" + "\n".join(offenders)
    )


def test_slide_over_close_button_uses_canonical_alpine_syntax() -> None:
    from lexigram.ui.organisms.slide_over import SlideOver

    html = str(SlideOver("Test", slide_id="test", is_open=True).render())
    assert 'x-on:click="open = false"' in html
    assert "x-on-click" not in html


def test_submit_button_loading_state_uses_canonical_alpine_syntax() -> None:
    from lexigram.ui.atoms.button import SubmitButton

    html = str(SubmitButton("Save").render())
    assert "x-on:click" in html
    assert "x-on:htmx:after-request" in html
    assert "x-on-click" not in html
    assert "x-on-htmx-after-request" not in html


def test_get_icon_is_decorative_by_default() -> None:
    from lexigram.ui.atoms.icons import get_icon

    html = str(get_icon("home"))
    assert 'aria-hidden="true"' in html
    assert 'focusable="false"' in html


def test_get_icon_respects_explicit_accessible_identity() -> None:
    from lexigram.ui.atoms.icons import get_icon

    html = str(get_icon("home", **{"aria-label": "Home", "role": "img"}))
    assert 'aria-label="Home"' in html
    assert "aria-hidden" not in html
