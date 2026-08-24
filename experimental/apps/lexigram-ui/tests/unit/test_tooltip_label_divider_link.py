"""Tests for Tooltip, Label, Divider, and Link atoms."""

from __future__ import annotations

from lexigram.ui.atoms.divider import Divider
from lexigram.ui.atoms.label import Label
from lexigram.ui.atoms.link import Link
from lexigram.ui.atoms.tooltip import Tooltip


class TestTooltip:
    def test_tooltip_renders_content(self) -> None:
        result = str(Tooltip("Helpful hint"))
        assert "Helpful hint" in result

    def test_tooltip_span_has_role_tooltip(self) -> None:
        result = str(Tooltip("Hint"))
        assert 'role="tooltip"' in result

    def test_tooltip_wrapper_has_aria_describedby(self) -> None:
        result = str(Tooltip("Hint"))
        assert "aria-describedby" in result

    def test_tooltip_id_matches_aria_describedby(self) -> None:
        tooltip = Tooltip("Hint", tooltip_id="tip-1")
        result = str(tooltip)
        assert 'id="tip-1"' in result
        assert 'aria-describedby="tip-1"' in result

    def test_tooltip_explicit_tooltip_id(self) -> None:
        result = str(Tooltip("Click me", tooltip_id="my-tooltip"))
        assert 'id="my-tooltip"' in result

    def test_tooltip_auto_generates_id(self) -> None:
        tooltip = Tooltip("Auto ID")
        result = str(tooltip)
        assert "tooltip-" in result

    def test_tooltip_position_default(self) -> None:
        tooltip = Tooltip("tip")
        assert tooltip.position == "top"

    def test_tooltip_custom_position_stored(self) -> None:
        tooltip = Tooltip("tip", position="bottom")
        assert tooltip.position == "bottom"

    def test_tooltip_wraps_children(self) -> None:
        from lexigram.ui.core.base import el

        tooltip = Tooltip("Hint")
        tooltip.children = [el("button", "Hover me")]
        result = str(tooltip)
        assert "Hover me" in result
        assert "Hint" in result


class TestLabel:
    def test_label_renders_text(self) -> None:
        result = str(Label("Username"))
        assert "Username" in result

    def test_label_renders_label_tag(self) -> None:
        result = str(Label("Name"))
        assert "<label" in result

    def test_label_for_attribute(self) -> None:
        result = str(Label("Email", for_="email-input"))
        assert 'for="email-input"' in result

    def test_label_required_shows_asterisk(self) -> None:
        result = str(Label("Password", required=True))
        assert "*" in result

    def test_label_required_indicator_aria_hidden(self) -> None:
        result = str(Label("Field", required=True))
        assert 'aria-hidden="true"' in result

    def test_label_not_required_no_asterisk(self) -> None:
        result = str(Label("Optional"))
        assert "*" not in result

    def test_label_size_sm_class(self) -> None:
        result = str(Label("X", size="sm"))
        assert "text-sm" in result

    def test_label_size_lg_class(self) -> None:
        result = str(Label("X", size="lg"))
        assert "text-lg" in result

    def test_label_muted_color(self) -> None:
        result = str(Label("Hint", muted=True))
        assert "text-muted-foreground" in result

    def test_label_default_weight_medium(self) -> None:
        result = str(Label("X"))
        assert "font-medium" in result

    def test_label_bold_weight(self) -> None:
        result = str(Label("X", weight="bold"))
        assert "font-bold" in result


class TestDivider:
    def test_horizontal_divider_renders_hr(self) -> None:
        result = str(Divider())
        assert "<hr" in result

    def test_horizontal_divider_has_border_t(self) -> None:
        result = str(Divider())
        assert "border-t" in result

    def test_vertical_divider_renders_div(self) -> None:
        result = str(Divider(orientation="vertical"))
        assert "<div" in result

    def test_vertical_divider_has_border_l(self) -> None:
        result = str(Divider(orientation="vertical"))
        assert "border-l" in result

    def test_custom_class_applied(self) -> None:
        result = str(Divider(class_name="my-divider"))
        assert "my-divider" in result


class TestLink:
    def test_link_renders_anchor(self) -> None:
        result = str(Link("Home", href="/"))
        assert "<a" in result
        assert "Home" in result

    def test_link_href_attribute(self) -> None:
        result = str(Link("About", href="/about"))
        assert 'href="/about"' in result

    def test_link_primary_variant(self) -> None:
        result = str(Link("Click", href="#", variant="primary"))
        assert "text-primary" in result

    def test_link_muted_variant(self) -> None:
        result = str(Link("Skip", href="#", variant="muted"))
        assert "text-muted-foreground" in result

    def test_link_default_variant(self) -> None:
        result = str(Link("Go", href="#"))
        assert "text-foreground" in result

    def test_link_size_lg(self) -> None:
        result = str(Link("Big", href="#", size="lg"))
        assert "text-lg" in result

    def test_link_custom_class(self) -> None:
        result = str(Link("X", href="#", class_="underline"))
        assert "underline" in result
