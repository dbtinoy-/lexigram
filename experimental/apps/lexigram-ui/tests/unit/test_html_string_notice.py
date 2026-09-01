"""A renderer returning an HTML string should read as text, not as breakage.

Strings are data under the escaping policy, so a ``Column.render()``
override that returns ``"<span>Active</span>"`` is escaped and the browser
shows ``&lt;span&gt;Active&lt;/span&gt;``. That is the correct security
behaviour, but on screen it looks like corrupted output rather than a
mistake in the code, and the existing warning only reaches the server log.

These tests pin two things: the value is presented as literal text in every
environment, and the developer-facing label appears *only* when component
debugging is on.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

import lexigram.ui.core.base as base
from lexigram.ui import render_to_string
from lexigram.ui.columns.types import TextColumn
from lexigram.ui.core.base import el, raw

HTML_STRING = "<span class='badge'>Active</span>"

#: Matches the heuristic but is ordinary product data, not a bug.
FALSE_POSITIVE = "List<String>"


@pytest.fixture(autouse=True)
def _reset_warning_state() -> Iterator[None]:
    """The warning dedupes globally, which would hide it from later tests."""
    base._warned_html_strings.clear()
    original = base._debug_components_cache
    yield
    base._debug_components_cache = original
    base._warned_html_strings.clear()


def _set_debug(enabled: bool) -> None:
    base._debug_components_cache = enabled


def _column(value: Any) -> Any:
    class _Col(TextColumn):
        def render(self, v: Any, record: Any = None) -> Any:
            return value

    return _Col("status")


def _cell(value: Any) -> str:
    return str(render_to_string(_column(value).render_cell({"status": "x"})))


class TestProductionRendering:
    def test_html_string_is_still_escaped(self) -> None:
        """The notice must not become a way to inject markup."""
        _set_debug(False)

        rendered = _cell(HTML_STRING)

        assert "<span class='badge'>" not in rendered
        assert "&lt;span class='badge'&gt;" in rendered

    def test_value_is_presented_as_literal_text(self) -> None:
        _set_debug(False)

        rendered = _cell(HTML_STRING)

        assert "<code" in rendered
        assert "font-mono" in rendered

    def test_no_developer_label_reaches_end_users(self) -> None:
        """The heuristic has false positives, so captioning a cell as a
        developer error in production would defame genuine data."""
        _set_debug(False)

        rendered = _cell(HTML_STRING)

        assert "unrendered HTML string" not in rendered

    def test_false_positive_is_not_labelled_in_production(self) -> None:
        _set_debug(False)

        rendered = _cell(FALSE_POSITIVE)

        assert "unrendered HTML string" not in rendered
        assert "List&lt;String&gt;" in rendered


class TestDebugRendering:
    def test_label_names_the_origin(self) -> None:
        _set_debug(True)

        rendered = _cell(HTML_STRING)

        assert "unrendered HTML string" in rendered
        assert "column 'status'" in rendered

    def test_label_carries_the_fix_in_a_tooltip(self) -> None:
        _set_debug(True)

        rendered = _cell(HTML_STRING)

        assert "raw()/Markup" in rendered

    def test_value_is_escaped_in_debug_too(self) -> None:
        _set_debug(True)

        rendered = _cell(HTML_STRING)

        assert "<span class='badge'>" not in rendered


class TestUnaffectedRenderers:
    """Only HTML-looking plain strings are rewritten."""

    def test_plain_text_is_untouched(self) -> None:
        _set_debug(True)

        rendered = _cell("Just text")

        assert "Just text" in rendered
        assert "<code" not in rendered

    def test_elements_are_untouched(self) -> None:
        _set_debug(True)

        rendered = _cell(el("span", "ok", class_="x"))

        assert '<span class="x">ok</span>' in rendered
        assert "<code" not in rendered

    def test_raw_html_still_renders_as_markup(self) -> None:
        """raw() is the documented way to opt into real HTML."""
        _set_debug(True)

        rendered = _cell(raw("<b>intentional</b>"))

        assert "<b>intentional</b>" in rendered
        assert "unrendered HTML string" not in rendered


class TestWarningStillLogs:
    """Adding the visible notice must not disable the log warning."""

    def test_warning_is_recorded_for_the_origin(self) -> None:
        _set_debug(False)

        _cell(HTML_STRING)

        # Asserts on the dedup registry rather than caplog: the logger is
        # structlog-backed, so caplog does not see these records.
        assert any(
            origin == "Column.render() for column 'status'"
            for origin, _ in base._warned_html_strings
        )

    def test_repeated_cells_warn_only_once(self) -> None:
        """A 50-row table must not log 50 identical warnings."""
        _set_debug(False)

        for _ in range(5):
            _cell(HTML_STRING)

        assert len(base._warned_html_strings) == 1


class TestCellCssClasses:
    """Cell classes are joined into the class attribute."""

    def test_classes_are_space_separated(self) -> None:
        """They were joined with "", producing "text-leftpx-6py-4" -- a
        single unknown class, so every cell lost its styling."""
        rendered = _cell("x")

        assert 'class="text-left px-6 py-4 whitespace-nowrap"' in rendered

    def test_wrap_and_copyable_classes_stay_separate(self) -> None:
        column = _column("x")
        column._wrap = True
        column._copyable = True

        rendered = str(render_to_string(column.render_cell({"status": "x"})))

        assert "whitespace-normal cursor-pointer" in rendered
        assert "py-4whitespace" not in rendered


class TestCopyableClipboardInjection:
    """The copy handler interpolates the cell value into JavaScript."""

    def _click_handler(self, value: str) -> str:
        import html as html_mod
        import re

        column = _column("x")
        column._copyable = True
        rendered = str(render_to_string(column.render_cell({"status": value})))
        match = re.search(r'hx-on-click="(.*?)" title', rendered)
        assert match is not None
        return html_mod.unescape(match.group(1))

    @pytest.mark.parametrize(
        "payload",
        [
            "');alert(1);//",
            # A backslash defeated the previous .replace("'", "\\'"): it
            # escaped the backslash, not the quote.
            "\\';alert(1);//",
            '");alert(1);//',
            "</script>",
        ],
    )
    def test_cell_value_cannot_escape_the_handler(self, payload: str) -> None:
        import json

        handler = self._click_handler(payload)
        literal = handler[len("navigator.clipboard.writeText(") : -1]

        assert json.loads(literal) == payload

    def test_apostrophe_still_copies_correctly(self) -> None:
        import json

        handler = self._click_handler("O'Brien")
        literal = handler[len("navigator.clipboard.writeText(") : -1]

        assert json.loads(literal) == "O'Brien"
