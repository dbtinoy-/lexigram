"""Tests for Badge, Spinner, and Icon atoms."""

from __future__ import annotations

from lexigram.ui.atoms.badge import Badge
from lexigram.ui.atoms.icon import Icon
from lexigram.ui.atoms.spinner import Spinner


class TestBadge:
    def test_badge_renders_text(self) -> None:
        result = str(Badge("New"))
        assert "New" in result

    def test_badge_is_not_a_live_region_by_default(self) -> None:
        """A static label must not be announced. role="status" makes
        assistive tech read the badge on every change, so a table full of
        them becomes unusable noise."""
        result = str(Badge("Active"))

        assert "role=" not in result
        assert "aria-live" not in result

    def test_badge_can_opt_into_a_live_region(self) -> None:
        result = str(Badge("Running", live=True))

        assert 'role="status"' in result
        assert 'aria-live="polite"' in result

    def test_badge_forwards_extra_props(self) -> None:
        result = str(Badge("X", title="Tooltip", id="b1"))

        assert 'title="Tooltip"' in result
        assert 'id="b1"' in result

    def test_badge_class_extends_rather_than_replaces_variant(self) -> None:
        """A caller-supplied class must not silently drop the styling."""
        result = str(Badge("X", variant="success", class_="ml-2"))

        assert "ml-2" in result
        assert "bg-success" in result

    def test_badge_default_variant_classes(self) -> None:
        result = str(Badge("X"))
        assert "bg-muted" in result

    def test_badge_success_variant(self) -> None:
        result = str(Badge("OK", variant="success"))
        assert "bg-success" in result

    def test_badge_danger_variant(self) -> None:
        result = str(Badge("Error", variant="danger"))
        assert "bg-destructive" in result

    def test_badge_warning_variant(self) -> None:
        result = str(Badge("Warn", variant="warning"))
        assert "bg-warning" in result

    def test_badge_primary_variant(self) -> None:
        result = str(Badge("Info", variant="primary"))
        assert "bg-primary" in result

    def test_badge_info_variant(self) -> None:
        result = str(Badge("i", variant="info"))
        assert "bg-info" in result

    def test_badge_renders_span_tag(self) -> None:
        result = str(Badge("tag"))
        assert "<span" in result

    def test_badge_rounded_full_class(self) -> None:
        result = str(Badge("X"))
        assert "rounded-full" in result

    def test_badge_shadcn_parity(self) -> None:
        html = str(Badge("New"))
        assert "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold" in html
        assert "border-transparent" in html


class TestSpinner:
    def test_spinner_renders_svg(self) -> None:
        result = str(Spinner())
        assert "<svg" in result

    def test_spinner_role_status(self) -> None:
        result = str(Spinner())
        assert 'role="status"' in result

    def test_spinner_aria_live_polite(self) -> None:
        result = str(Spinner())
        assert 'aria-live="polite"' in result

    def test_spinner_default_aria_label(self) -> None:
        result = str(Spinner())
        assert 'aria-label="Loading..."' in result

    def test_spinner_custom_aria_label(self) -> None:
        result = str(Spinner(aria_label="Processing request"))
        assert 'aria-label="Processing request"' in result

    def test_spinner_size_sm(self) -> None:
        result = str(Spinner(size="sm"))
        assert "w-4" in result
        assert "h-4" in result

    def test_spinner_size_md(self) -> None:
        result = str(Spinner(size="md"))
        assert "w-6" in result
        assert "h-6" in result

    def test_spinner_size_lg(self) -> None:
        result = str(Spinner(size="lg"))
        assert "w-8" in result
        assert "h-8" in result

    def test_spinner_size_xl(self) -> None:
        result = str(Spinner(size="xl"))
        assert "w-12" in result
        assert "h-12" in result

    def test_spinner_color_class(self) -> None:
        result = str(Spinner(color="blue"))
        assert "text-primary" in result

    def test_spinner_animate_spin_class(self) -> None:
        result = str(Spinner())
        assert "animate-spin" in result

    def test_spinner_default_color_primary(self) -> None:
        result = str(Spinner())
        assert "text-primary" in result


class TestIcon:
    def test_icon_renders_svg_for_known_name(self) -> None:
        result = str(Icon("home"))
        assert "<svg" in result

    def test_icon_aria_hidden_true_by_default(self) -> None:
        result = str(Icon("home"))
        assert 'aria-hidden="true"' in result

    def test_icon_aria_hidden_explicit_true(self) -> None:
        result = str(Icon("home", aria_hidden=True))
        assert 'aria-hidden="true"' in result

    def test_icon_aria_hidden_false_omits_aria_hidden(self) -> None:
        result = str(Icon("home", aria_hidden=False))
        assert 'aria-hidden="true"' not in result

    def test_icon_aria_label_when_not_hidden(self) -> None:
        result = str(Icon("home", aria_hidden=False, aria_label="Go home"))
        assert 'aria-label="Go home"' in result

    def test_icon_no_aria_label_when_hidden(self) -> None:
        result = str(Icon("home", aria_hidden=True, aria_label="ignored"))
        assert "aria-label" not in result

    def test_icon_custom_size(self) -> None:
        result = str(Icon("home", size="w-8 h-8"))
        assert "w-8" in result

    def test_icon_custom_class_name(self) -> None:
        result = str(Icon("home", class_name="text-red-500"))
        assert "text-red-500" in result

    def test_icon_unknown_name_renders_span(self) -> None:
        result = str(Icon("not-an-icon-name-at-all-123"))
        assert "<span" in result or result == ""
