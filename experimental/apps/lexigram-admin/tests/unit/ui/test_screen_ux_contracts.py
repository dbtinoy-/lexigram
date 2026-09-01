"""UX and accessibility contracts for the dashboard, infrastructure, and
tenancy/impersonation screens.

These pin behaviour that is easy to regress silently during styling work:
a control that is only reachable by mouse, a loading state that never
resolves, a colour pair that drops below contrast minimums, or a
script-dependent control with no fallback. Each test states the user-facing
consequence rather than just asserting on markup.
"""

from __future__ import annotations

import re
import types

import pytest

from lexigram.admin.clusters.registry import INFRASTRUCTURE_CLUSTER
from lexigram.admin.controllers.clusters import ClusterCenterController
from lexigram.admin.dashboard.widget_cards import WidgetRegistry
from lexigram.admin.ui.organisms.topbar import TenantSwitcher
from lexigram.admin.ui.templates.shell_sections import build_impersonation_banner
from lexigram.contracts.admin.types import (
    DashboardWidgetDefinition,
    WidgetCategory,
    WidgetKind,
    WidgetSize,
)
from lexigram.ui import render_to_string


def _widget(name: str = "users", title: str = "Users") -> DashboardWidgetDefinition:
    return DashboardWidgetDefinition(
        name=name,
        title=title,
        contributor="core",
        render_endpoint=f"/admin/w/{name}",
        view_kind=WidgetKind.STAT,
        size=WidgetSize.SMALL,
        category=WidgetCategory.CUSTOM,
        order=1,
    )


def _relative_luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(foreground: str, background: str) -> float:
    lighter = max(_relative_luminance(foreground), _relative_luminance(background))
    darker = min(_relative_luminance(foreground), _relative_luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


class TestDashboardWidgetCards:
    """Widget cards must be operable and must never look stuck."""

    def test_config_control_has_an_accessible_name(self) -> None:
        """A bare cog glyph is announced as nothing useful on its own."""
        html = WidgetRegistry().render_contributor_widgets([_widget()])

        assert 'aria-label="Configure Users widget"' in html

    def test_config_control_is_reachable_without_a_mouse(self) -> None:
        """opacity-0 revealed only on hover strands keyboard users."""
        html = WidgetRegistry().render_contributor_widgets([_widget()])

        assert "group-focus-within:opacity-100" in html

    def test_config_control_is_a_button_not_a_submit(self) -> None:
        html = WidgetRegistry().render_contributor_widgets([_widget()])

        assert 'type="button"' in html

    def test_skeleton_bars_are_hidden_from_assistive_tech(self) -> None:
        """Three anonymous boxes convey nothing; one spoken message does."""
        html = WidgetRegistry().render_contributor_widgets([_widget()])

        assert 'aria-hidden="true"' in html
        assert "Loading Users…" in html

    def test_skeleton_respects_reduced_motion(self) -> None:
        html = WidgetRegistry().render_contributor_widgets([_widget()])

        assert "motion-reduce:animate-none" in html

    def test_body_announces_its_busy_state(self) -> None:
        html = WidgetRegistry().render_contributor_widgets([_widget()])

        assert 'aria-busy="true"' in html

    def test_every_widget_is_retryable(self) -> None:
        """The retry after a failure re-fires through the live-refresh trigger,
        so a non-live widget must listen for it too — otherwise the widget
        that failed is precisely the one that cannot be retried."""
        html = WidgetRegistry().render_contributor_widgets([_widget()])

        # Assert on the trigger attribute itself rather than a bare substring:
        # "live-refresh" also occurs inside the emitted scripts, so a loose
        # check would pass even with the trigger removed. The polling clause
        # in between depends on the widget's refresh interval, so match the
        # attribute and inspect its contents.
        triggers = re.findall(r'hx-trigger="([^"]*)"', html)

        assert triggers, "widget body must declare an hx-trigger"
        assert all("live-refresh" in trigger for trigger in triggers)

    def test_failure_handling_is_emitted(self) -> None:
        """HTMX does not swap non-2xx, so without this the skeleton pulses
        forever and a failure is indistinguishable from a slow request."""
        html = WidgetRegistry().render_contributor_widgets([_widget()])

        assert "htmx:responseError" in html
        assert "htmx:sendError" in html
        assert "Retry" in html

    def test_failure_handler_is_installed_once(self) -> None:
        """Per-card handlers would grow the cost with dashboard size."""
        html = WidgetRegistry().render_contributor_widgets(
            [_widget("a", "A"), _widget("b", "B"), _widget("c", "C")]
        )

        assert html.count("__lexigramWidgetState") == 2  # guard read + guard set

    def test_error_copy_distinguishes_permission_from_outage(self) -> None:
        """"Something went wrong" for a 403 sends the operator debugging the
        wrong thing."""
        html = WidgetRegistry().render_contributor_widgets([_widget()])

        assert "do not have access" in html
        assert "could not be loaded" in html


class TestInfrastructureCards:
    """Cluster cards must be fully clickable and validly structured."""

    @pytest.fixture
    def controller(self) -> ClusterCenterController:
        instance = ClusterCenterController.__new__(ClusterCenterController)
        instance._cluster = INFRASTRUCTURE_CLUSTER
        return instance

    @pytest.fixture
    def card_html(self, controller: ClusterCenterController) -> str:
        item = types.SimpleNamespace(
            label="Web",
            icon="globe",
            url="/admin/web",
            children=[types.SimpleNamespace(label="Routes", url="/admin/web/routes")],
        )
        return render_to_string(controller._render_card(item))

    def test_icon_size_classes_are_not_duplicated(self, card_html: str) -> None:
        """get_icon already emits its own size classes."""
        assert "w-5 h-5 w-5 h-5" not in card_html

    def test_icon_is_decorative(self, card_html: str) -> None:
        assert 'aria-hidden="true"' in card_html

    def test_whole_card_is_clickable(self, card_html: str) -> None:
        """The card-wide hover style promises a card-wide target."""
        assert "stretched-link" in card_html

    def test_child_links_are_a_real_list(self, card_html: str) -> None:
        """Nesting them inside the card link is invalid and breaks the
        keyboard order."""
        assert "<ul" in card_html
        assert "<li>" in card_html

    def test_child_links_are_labelled_as_a_group(self, card_html: str) -> None:
        assert 'aria-label="Web sections"' in card_html

    def test_child_links_stay_above_the_stretched_overlay(
        self, card_html: str
    ) -> None:
        """Otherwise the card link swallows every sub-link."""
        assert "cluster-card" in card_html

    def test_links_have_visible_focus(self, card_html: str) -> None:
        assert "focus-visible:ring-2" in card_html

    def test_empty_state_explains_how_areas_appear(
        self, controller: ClusterCenterController
    ) -> None:
        """An empty cluster is configuration, not failure; say what to do."""
        html = render_to_string(controller._render_overview([]))

        assert "contributes" in html
        assert 'role="status"' in html


class TestTenantSwitcher:
    """Switching tenant changes whose data is being edited."""

    @pytest.fixture
    def html(self) -> str:
        return render_to_string(
            TenantSwitcher(
                tenants=[("acme", "Acme Corp"), ("globex", "Globex")],
                current_tenant_id="acme",
                csrf_token="tok",
            )
        )

    def test_control_is_labelled(self, html: str) -> None:
        """Unlabelled, it is announced only as its value — indistinguishable
        from a language or theme picker."""
        assert 'aria-label="Active tenant"' in html
        assert "<label" in html

    def test_consequence_is_described(self, html: str) -> None:
        assert "switches the active tenant" in html

    def test_current_tenant_is_named(self, html: str) -> None:
        assert "Currently viewing Acme Corp" in html

    def test_has_a_no_script_fallback(self, html: str) -> None:
        """Auto-submit is JS-only; without a fallback a scripting failure
        leaves the operator believing they switched tenant when they did
        not."""
        assert "tenant-switch-fallback" in html
        assert 'type="submit"' in html

    def test_still_renders_nothing_without_tenants(self) -> None:
        assert render_to_string(TenantSwitcher(tenants=[])) == ""

    def test_csrf_token_is_still_carried(self, html: str) -> None:
        assert 'name="csrf_token"' in html


class TestImpersonationBanner:
    """The highest-consequence state in the admin must be unmissable."""

    @pytest.fixture
    def html(self) -> str:
        return render_to_string(
            build_impersonation_banner(True, "user-42", "tok")
        )

    def test_inactive_renders_nothing(self) -> None:
        assert build_impersonation_banner(False, "user-42", "tok") == ""

    def test_state_is_announced(self, html: str) -> None:
        assert 'role="status"' in html
        assert 'aria-live="polite"' in html

    def test_target_identity_is_shown(self, html: str) -> None:
        assert "user-42" in html

    def test_consequence_is_stated_for_screen_readers(self, html: str) -> None:
        assert "recorded against this account" in html

    def test_stop_button_names_its_target(self, html: str) -> None:
        """"Stop impersonating" alone is ambiguous out of context."""
        assert 'aria-label="Stop impersonating user-42"' in html

    def test_not_signalled_by_colour_alone(self, html: str) -> None:
        assert "Impersonating" in html
        assert "<svg" in html

    def test_background_meets_wcag_aa(self, html: str) -> None:
        """White on amber-600 is 3.19:1, under the 4.5:1 minimum."""
        assert "bg-amber-700" in html
        assert "bg-amber-600" not in html

    def test_csrf_token_is_still_carried(self, html: str) -> None:
        assert 'value="tok"' in html


class TestContrastMath:
    """The contrast claim above is arithmetic, not opinion."""

    def test_amber_600_fails_aa_for_body_text(self) -> None:
        assert _contrast("ffffff", "d97706") < 4.5

    def test_amber_700_passes_aa_for_body_text(self) -> None:
        assert _contrast("ffffff", "b45309") >= 4.5

    def test_amber_800_passes_aa_for_body_text(self) -> None:
        assert _contrast("ffffff", "92400e") >= 4.5


class TestDashboardEmptyState:
    """An empty dashboard must not misattribute its own cause."""

    @pytest.fixture
    def html(self) -> str:
        return WidgetRegistry().render_contributor_widgets([])

    def test_is_announced(self, html: str) -> None:
        assert 'role="status"' in html

    def test_does_not_assert_nothing_is_configured(self, html: str) -> None:
        """The list is also emptied by the assembler's permission filter, so
        claiming "none configured" sends the operator to inspect config when
        the real cause may be their own access."""
        assert "No contributor widgets configured" not in html

    def test_names_both_possible_causes(self, html: str) -> None:
        assert "contributor registers" in html
        assert "permission" in html

    def test_decorative_icon_is_hidden(self, html: str) -> None:
        assert 'aria-hidden="true"' in html


class TestAreaDescriptions:
    """Area copy belongs to the contributing package, not a hardcoded map."""

    def _controller(self, cluster: object) -> ClusterCenterController:
        instance = ClusterCenterController.__new__(ClusterCenterController)
        instance._cluster = cluster
        return instance

    def _area(self, label: str, description: str = "") -> types.SimpleNamespace:
        return types.SimpleNamespace(
            label=label,
            icon="globe",
            url="/x",
            children=[],
            description=description,
        )

    def test_contributed_description_wins(self) -> None:
        controller = self._controller(INFRASTRUCTURE_CLUSTER)

        assert (
            controller._describe(self._area("Web", "Package-owned copy."))
            == "Package-owned copy."
        )

    def test_falls_back_to_legacy_map_for_builtin_areas(self) -> None:
        """Built-in areas predate the contract field; they must not regress."""
        controller = self._controller(INFRASTRUCTURE_CLUSTER)

        assert "HTTP routing" in controller._describe(self._area("Web"))

    def test_tolerates_contributions_without_the_field(self) -> None:
        """The field is new; older contributions simply lack the attribute."""
        controller = self._controller(INFRASTRUCTURE_CLUSTER)
        legacy = types.SimpleNamespace(
            label="Web", icon="globe", url="/x", children=[]
        )

        assert "HTTP routing" in controller._describe(legacy)

    def test_blank_description_is_treated_as_unset(self) -> None:
        controller = self._controller(INFRASTRUCTURE_CLUSTER)

        assert "HTTP routing" in controller._describe(self._area("Web", "   "))

    def test_generic_fallback_names_the_actual_cluster(self) -> None:
        """The controller is generic; asserting "infrastructure" on a Content
        landing page is simply false."""
        controller = self._controller(
            types.SimpleNamespace(
                name="content", label="Content", group="content"
            )
        )

        assert controller._describe(self._area("Widgets")) == (
            "Manage and monitor this content area."
        )

    def test_legacy_map_does_not_leak_across_clusters(self) -> None:
        """The map is keyed on label alone, so a "Web" area in another
        cluster would otherwise inherit infrastructure copy."""
        controller = self._controller(
            types.SimpleNamespace(
                name="content", label="Content", group="content"
            )
        )

        assert "HTTP routing" not in controller._describe(self._area("Web"))

    def test_contract_exposes_the_field(self) -> None:
        from lexigram.contracts.admin.types import NavigationContribution

        assert NavigationContribution(label="A", url="/a").description == ""
