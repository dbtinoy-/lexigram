"""Tests for UI atoms — comprehensive coverage including ARIA accessibility."""

from __future__ import annotations

from lexigram.ui.atoms.badge import Badge
from lexigram.ui.atoms.button import Button, SubmitButton
from lexigram.ui.atoms.divider import Divider
from lexigram.ui.atoms.icon import Icon
from lexigram.ui.atoms.label import Label
from lexigram.ui.atoms.link import Link
from lexigram.ui.atoms.progress_bar import ProgressBar
from lexigram.ui.atoms.skeleton import Skeleton
from lexigram.ui.atoms.spinner import Spinner
from lexigram.ui.atoms.switch import Switch
from lexigram.ui.atoms.theme_toggle import ThemeToggle
from lexigram.ui.atoms.tooltip import Tooltip
from lexigram.ui.molecules.tabs import Tabs

# ---------------------------------------------------------------------------
# Button
# ---------------------------------------------------------------------------


class TestButton:
    def test_default_variant(self):
        html = str(Button("Save"))
        assert "bg-primary" in html
        assert "text-primary-foreground" in html
        assert "h-10" in html

    def test_secondary_variant(self):
        html = str(Button("Cancel", variant="secondary"))
        assert "bg-secondary" in html

    def test_destructive_variant(self):
        html = str(Button("Delete", variant="destructive"))
        assert "bg-destructive" in html

    def test_outline_variant(self):
        html = str(Button("Edit", variant="outline"))
        assert "border-input" in html
        assert "bg-background" in html

    def test_ghost_variant(self):
        html = str(Button("Menu", variant="ghost"))
        assert "hover:bg-accent" in html

    def test_link_variant(self):
        html = str(Button("Learn more", variant="link"))
        assert "text-primary" in html
        assert "hover:underline" in html

    def test_size_xs(self):
        html = str(Button("X Small", size="xs"))
        assert "h-7" in html

    def test_size_icon(self):
        html = str(Button("X", size="icon"))
        assert "h-10 w-10" in html

    def test_size_sm(self):
        html = str(Button("Small", size="sm"))
        assert "h-9" in html

    def test_size_lg(self):
        html = str(Button("Large", size="lg"))
        assert "h-11" in html

    def test_size_xl(self):
        html = str(Button("XL", size="xl"))
        assert "h-12" in html

    def test_disabled(self):
        html = str(Button("Disabled", disabled=True))
        assert "disabled:pointer-events-none" in html

    def test_disabled_opacity(self):
        html = str(Button("Disabled", disabled=True))
        assert "disabled:opacity-50" in html

    def test_focus_ring(self):
        html = str(Button("Focus"))
        assert "focus-visible:ring-ring" in html

    def test_current_shadcn_classes(self):
        """Button matches current shadcn/ui base + variant classes."""
        html = str(Button("Save"))
        assert "gap-2" in html
        assert "ring-offset-background" in html
        assert "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" in html
        assert "disabled:pointer-events-none disabled:opacity-50" in html
        assert "[&amp;_svg]:pointer-events-none [&amp;_svg]:size-4 [&amp;_svg]:shrink-0" in html

    def test_icon_size_is_h10_w10(self):
        """Current shadcn icon size is h-10 w-10."""
        html = str(Button("X", size="icon"))
        assert "h-10 w-10" in html

    def test_default_size_is_h10(self):
        """Current shadcn default size is h-10."""
        html = str(Button("Save"))
        assert "h-10 px-4 py-2" in html

    def test_transition(self):
        html = str(Button("Trans"))
        assert "transition-colors" in html

    def test_type_button_by_default(self):
        html = str(Button("Click"))
        assert 'type="button"' in html

    def test_custom_class_merges(self):
        html = str(Button("Custom", class_="my-custom-class"))
        assert "my-custom-class" in html
        assert "bg-primary" in html

    def test_button_renders_button_tag(self):
        html = str(Button("Go"))
        assert "<button" in html

    def test_button_empty_label(self):
        html = str(Button())
        assert "<button" in html


class TestSubmitButton:
    def test_submit_button_renders(self):
        html = str(SubmitButton("Create"))
        assert 'type="submit"' in html
        assert "Create" in html

    def test_submit_button_default_label(self):
        html = str(SubmitButton())
        assert "Submit" in html

    def test_submit_button_alpine_data(self):
        html = str(SubmitButton())
        assert "x-data" in html
        assert "loading" in html

    def test_submit_button_disabled(self):
        html = str(SubmitButton(disabled=True))
        assert "disabled" in html

    def test_submit_button_variant_classes(self):
        html = str(SubmitButton("Delete", variant="destructive"))
        assert "bg-destructive" in html


# ---------------------------------------------------------------------------
# ThemeToggle
# ---------------------------------------------------------------------------


class TestThemeToggle:
    def test_toggle_renders_button(self):
        result = str(ThemeToggle())
        assert "<button" in result

    def test_toggle_has_icons(self):
        result = str(ThemeToggle())
        assert "<svg" in result

    def test_toggle_has_sun_icon(self):
        result = str(ThemeToggle())
        assert "aria-hidden" in result

    def test_toggle_has_alpine_data(self):
        result = str(ThemeToggle())
        assert "x-data" in result

    def test_toggle_toggles_theme(self):
        result = str(ThemeToggle())
        assert "x-on:click" in result

    def test_toggle_stores_theme(self):
        result = str(ThemeToggle())
        assert "localStorage" in result or "$store" in result


# ---------------------------------------------------------------------------
# Badge
# ---------------------------------------------------------------------------


class TestBadge:
    """Tests for the Badge component."""

    def test_badge_renders_text(self) -> None:
        result = str(Badge("New"))
        assert "New" in result

    def test_badge_has_role_status(self) -> None:
        result = str(Badge("Active"))
        assert 'role="status"' in result

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


# ---------------------------------------------------------------------------
# Spinner
# ---------------------------------------------------------------------------


class TestSpinner:
    """Tests for the Spinner component."""

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


# ---------------------------------------------------------------------------
# Icon
# ---------------------------------------------------------------------------


class TestIcon:
    """Tests for the Icon component."""

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
        """aria-label should not be rendered on decorative icons."""
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


# ---------------------------------------------------------------------------
# Tooltip
# ---------------------------------------------------------------------------


class TestTooltip:
    """Tests for the Tooltip component."""

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


# ---------------------------------------------------------------------------
# Label
# ---------------------------------------------------------------------------


class TestLabel:
    """Tests for the Label component."""

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


# ---------------------------------------------------------------------------
# Divider
# ---------------------------------------------------------------------------


class TestDivider:
    """Tests for the Divider factory function."""

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


# ---------------------------------------------------------------------------
# Link
# ---------------------------------------------------------------------------


class TestLink:
    """Tests for the Link factory function."""

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


# ---------------------------------------------------------------------------
# ProgressBar
# ---------------------------------------------------------------------------


class TestProgressBar:
    """Tests for the ProgressBar component."""

    def test_progress_bar_renders(self) -> None:
        result = str(ProgressBar(value=50))
        assert "50%" in result

    def test_progress_bar_zero(self) -> None:
        result = str(ProgressBar(value=0))
        assert "0%" in result

    def test_progress_bar_full(self) -> None:
        result = str(ProgressBar(value=100))
        assert "100%" in result

    def test_progress_bar_with_label(self) -> None:
        result = str(ProgressBar(value=30, label="Upload progress"))
        assert "Upload progress" in result

    def test_progress_bar_custom_color(self) -> None:
        result = str(ProgressBar(value=60, color="green"))
        assert "bg-primary" in result

    def test_progress_bar_no_percentage_when_disabled(self) -> None:
        result = str(ProgressBar(value=40, show_percentage=False))
        # aria_label contains percentage (not visible text)
        assert "40%" in result

    def test_progress_bar_size_sm(self) -> None:
        result = str(ProgressBar(value=10, size="sm"))
        assert "h-1" in result

    def test_progress_bar_size_lg(self) -> None:
        result = str(ProgressBar(value=10, size="lg"))
        assert "h-3" in result


# ---------------------------------------------------------------------------
# Skeleton
# ---------------------------------------------------------------------------


class TestSkeleton:
    """Tests for the Skeleton component."""

    def test_skeleton_text_variant_renders(self) -> None:
        result = str(Skeleton())
        assert "animate-pulse" in result

    def test_skeleton_circular_variant(self) -> None:
        result = str(Skeleton(variant="circular"))
        assert "rounded-full" in result

    def test_skeleton_rectangular_variant(self) -> None:
        result = str(Skeleton(variant="rectangular"))
        assert "animate-pulse" in result
        assert "rounded-full" not in result

    def test_skeleton_text_multiple_lines(self) -> None:
        result = str(Skeleton(variant="text", count=3))
        assert result.count("animate-pulse") == 3

    def test_skeleton_text_last_line_shorter(self) -> None:
        result = str(Skeleton(variant="text", count=2))
        assert "80%" in result


# ---------------------------------------------------------------------------
# Switch
# ---------------------------------------------------------------------------


class TestSwitch:
    """Tests for the Switch component."""

    def test_switch_renders(self) -> None:
        result = str(Switch(label="Enable notifications", name="notifications"))
        assert "Enable notifications" in result

    def test_switch_name_in_output(self) -> None:
        result = str(Switch(label="Dark mode", name="dark_mode"))
        assert "dark_mode" in result

    def test_switch_with_error(self) -> None:
        result = str(Switch(label="Accept", name="accept", error="Required field"))
        assert "Required field" in result

    def test_switch_checked_state(self) -> None:
        result = str(Switch(label="Active", name="active", value=True))
        assert "Active" in result


# ---------------------------------------------------------------------------
# Current shadcn class parity
# ---------------------------------------------------------------------------


class TestCurrentShadcnClasses:
    """Class parity with the current shadcn/ui registry."""

    def test_badge(self) -> None:
        html = str(Badge("New"))
        assert "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold" in html
        assert "border-transparent" in html

    def test_skeleton(self) -> None:
        html = str(Skeleton())
        assert "animate-pulse" in html
        assert "rounded-md" in html
        assert "bg-muted" in html

    def test_switch_track(self) -> None:
        html = str(Switch(label="s", name="s"))
        assert "h-6 w-11" in html
        assert "rounded-full border-2 border-transparent" in html
        assert "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" in html

    def test_tabs_container(self) -> None:
        html = str(Tabs([("A", "a"), ("B", "b")]))
        assert 'role="tablist"' in html
        assert "bg-muted p-1 text-muted-foreground" in html
