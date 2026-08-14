"""Accessibility contracts for Select components."""

from __future__ import annotations

from lexigram.ui.atoms.inputs.selection.select import Select
from lexigram.ui.molecules.rich_select import RichSelect


class TestSelectA11y:
    def test_select_has_label_wiring(self) -> None:
        html = str(Select(name="s", choices=[("a", "Alpha")], label="Pick one"))
        assert 'id="' in html
        assert 'for="' in html or "aria-labelledby" in html

    def test_select_native_uses_select_element(self) -> None:
        html = str(Select(name="s", choices=[("a", "Alpha")]))
        assert "<select" in html
        assert "<option" in html

    def test_select_error_aria(self) -> None:
        html = str(
            Select(
                name="s",
                choices=[("a", "Alpha")],
                label="Pick one",
                error="Choose an option",
            )
        )
        assert 'aria-invalid="true"' in html
        assert "aria-describedby" in html

    def test_select_required_aria(self) -> None:
        html = str(Select(name="s", choices=[("a", "Alpha")], required=True))
        assert 'aria-required="true"' in html


class TestRichSelectA11y:
    def test_rich_select_combobox_role(self) -> None:
        html = str(RichSelect(label="Choose", name="s", options=[{"value": "a", "label": "Alpha"}]))
        assert 'role="combobox"' in html
        assert 'aria-expanded="false"' in html or ":aria-expanded" in html
        assert "aria-controls" in html

    def test_rich_select_listbox(self) -> None:
        html = str(
            RichSelect(
                label="Choose",
                name="s",
                options=[{"value": "a", "label": "Alpha"}, {"value": "b", "label": "Beta"}],
            )
        )
        assert 'role="listbox"' in html
        assert 'role="option"' in html