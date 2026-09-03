"""R17 accessibility regression guards.

Covers the fixes from docs/09-01-2026/13-a11y-and-dead-handlers.md:

* B13 — Alpine ``x_on_*`` kwargs render as dead ``x-on-*`` attributes
  (Alpine only binds ``x-on:event``/``@event``). The command palette's
  keyboard navigation and option clicks were completely dead because of
  this. A source scan keeps the class from coming back. The htmx
  ``hx_on_*`` alias is valid (htmx supports all-dash ``hx-on-``) and is
  therefore allowed.
* Command palette combobox pattern + unique option ids + focus trap.
* Unique per-row checkbox ids in table views.
* Labeled flash-notification close buttons.
* "Showing X to Y of Z" result counts announced as polite live regions.
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[3] / "src" / "lexigram" / "admin"

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
        'canonical name instead, e.g. el("li", {"x-on:click": "..."}). '
        "Offending lines:\n" + "\n".join(offenders)
    )


class TestCommandPaletteA11y:
    def _html(self) -> str:
        from lexigram.admin.ui.organisms.command_palette import CommandPalette

        return str(CommandPalette().render())

    def test_keyboard_navigation_uses_canonical_alpine_syntax(self) -> None:
        html = self._html()
        assert 'x-on:keydown.down.prevent="next()"' in html
        assert 'x-on:keydown.up.prevent="prev()"' in html
        assert 'x-on:keydown.enter.prevent="execute()"' in html
        # The dead forms must never come back.
        assert "x-on-keydown" not in html
        assert "x-on-click" not in html
        assert "x-on-mouseenter" not in html

    def test_option_activation_uses_canonical_alpine_syntax(self) -> None:
        html = self._html()
        assert 'x-on:click="execute(index)"' in html
        assert 'x-on:mouseenter="selectedIndex = index"' in html

    def test_input_exposes_combobox_pattern(self) -> None:
        html = self._html()
        assert 'role="combobox"' in html
        assert 'aria-expanded="true"' in html
        assert 'aria-controls="command-palette-options"' in html
        assert 'aria-autocomplete="list"' in html
        assert "aria-activedescendant" in html
        assert 'aria-label="Search commands and navigation"' in html

    def test_options_have_unique_bound_ids_and_selection_state(self) -> None:
        html = self._html()
        assert 'id="command-palette-options"' in html
        # el() HTML-escapes attribute values, so the single quotes in the
        # Alpine :id binding render as &#x27;.
        assert ":id=\"&#x27;command-palette-option-&#x27; + index\"" in html
        assert ":aria-selected=" in html
        # The old static duplicate id must not come back.
        assert 'id="option-1"' not in html

    def test_dialog_traps_focus_and_is_labeled(self) -> None:
        html = self._html()
        assert 'x-trap.noscroll="open"' in html
        assert 'aria-label="Command palette"' in html
        assert 'role="dialog"' in html
        assert 'aria-modal="true"' in html


def test_flash_close_buttons_are_labeled() -> None:
    from lexigram.admin.ui.templates import shell_scripts

    source = Path(shell_scripts.__file__).read_text(encoding="utf-8")
    closers = re.findall(r"<button[^>]*closest\('\[role=alert\]'\)[^>]*>", source)
    assert closers, "expected flash close buttons in shell_scripts.py"
    for button in closers:
        assert 'aria-label="Dismiss notification"' in button
        assert 'type="button"' in button


def test_table_views_render_unique_row_checkbox_ids() -> None:
    views = SRC / "ui" / "organisms" / "table" / "views"
    expected = {
        "tabular_rows.py": 'id=f"row-select-{rid}"',
        "grid.py": 'id=f"grid-select-{rid}"',
        "stacked.py": 'id=f"stacked-select-{rid}"',
        "calendar.py": 'id=f"calendar-select-{rid}"',
    }
    for filename, marker in expected.items():
        source = (views / filename).read_text(encoding="utf-8")
        assert marker in source, (
            f"{filename}: row checkboxes must carry unique ids — every row "
            'previously rendered the duplicate id="ids"'
        )


def test_result_counts_are_polite_live_regions() -> None:
    for rel in ("ui/organisms/pagination.py", "dashboard/page_renderer.py"):
        source = (SRC / rel).read_text(encoding="utf-8")
        showing = source.index('"Showing ",')
        window = source[max(0, showing - 600) : showing]
        assert '"role": "status"' in window and '"aria-live": "polite"' in window, (
            f"{rel}: the 'Showing X to Y of Z' block must be a polite live "
            "region so HTMX swaps announce result changes"
        )
