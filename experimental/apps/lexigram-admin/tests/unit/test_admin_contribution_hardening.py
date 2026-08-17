"""Tests for admin contributor metadata hardening (version + package_source)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.contributors.base import BaseAdminContributor


class TestContributorMetadata:
    def test_base_contributor_has_version(self) -> None:
        class MyContributor(BaseAdminContributor):
            name = "my"
            display_name = "My"

        c = MyContributor()
        assert c.version == "0.0.0"
        assert c.package_source == "built-in"

    def test_contributor_version_is_overridable(self) -> None:
        class MyContributor(BaseAdminContributor):
            name = "my"
            display_name = "My"
            version = "1.2.3"
            package_source = "mypackage"

        c = MyContributor()
        assert c.version == "1.2.3"
        assert c.package_source == "mypackage"


from lexigram.contracts.admin.types import (
    ActionParameterField,
    ActionParameterSchema,
    AdminActionDefinition,
)


class TestActionParameterSchema:
    def test_action_parameter_field_is_frozen(self) -> None:
        field = ActionParameterField(name="target", type_hint="str", required=True)
        with pytest.raises(AttributeError):
            field.name = "other"  # type: ignore[misc]

    def test_action_definition_accepts_parameter_schema(self) -> None:
        schema = ActionParameterSchema(
            fields=(
                ActionParameterField(name="target", type_hint="str", required=True),
            )
        )
        action = AdminActionDefinition(
            name="flush_cache",
            title="Flush Cache",
            contributor="cache",
            handler="lexigram.cache.admin:flush_cache",
            parameter_schema=schema,
        )
        assert action.parameter_schema is not None
        assert len(action.parameter_schema.fields) == 1

    def test_action_definition_parameter_schema_defaults_none(self) -> None:
        action = AdminActionDefinition(
            name="flush_all",
            title="Flush All",
            contributor="cache",
            handler="lexigram.cache.admin:flush_all",
        )
        assert action.parameter_schema is None


from lexigram.admin.contributors.exceptions import (
    ContributorNotFoundError,
    ContributorPermissionError,
)
from lexigram.admin.dashboard.assembler import DashboardAssembler


class TestRBACEnforcement:
    def _make_assembler(self) -> DashboardAssembler:
        contributor = MagicMock()
        contributor.contributor_id = "cache"
        contributor.required_permissions = frozenset({"admin.cache.flush"})
        contributor.get_actions.return_value = [
            AdminActionDefinition(
                name="flush",
                title="Flush Cache",
                contributor="cache",
                handler="some.module:flush",
            )
        ]
        contributor.get_widgets.return_value = []
        contributor.get_navigation.return_value = []
        return DashboardAssembler(contributors=[contributor])

    @pytest.mark.asyncio
    async def test_execute_action_raises_permission_error_when_missing_perm(
        self,
    ) -> None:
        assembler = self._make_assembler()
        with pytest.raises(ContributorPermissionError):
            await assembler.execute_action(
                contributor_id="cache",
                action_name="flush",
                params={},
                user_permissions=frozenset(),  # no perms
            )

    @pytest.mark.asyncio
    async def test_execute_action_raises_not_found_for_unknown_contributor(
        self,
    ) -> None:
        assembler = self._make_assembler()
        with pytest.raises(ContributorNotFoundError):
            await assembler.execute_action(
                contributor_id="unknown",
                action_name="flush",
                params={},
                user_permissions=frozenset({"admin.cache.flush"}),
            )

    @pytest.mark.asyncio
    async def test_execute_action_succeeds_with_correct_permissions(self) -> None:
        assembler = self._make_assembler()
        contributor = assembler._contributors_by_id["cache"]
        contributor.execute_action = AsyncMock(return_value={"status": "ok"})
        result = await assembler.execute_action(
            contributor_id="cache",
            action_name="flush",
            params={},
            user_permissions=frozenset({"admin.cache.flush"}),
        )
        assert result == {"status": "ok"}


import structlog.testing

from lexigram.contracts.admin import DashboardWidgetDefinition, WidgetKind


class TestContributionConflictDetection:
    """Tests that DashboardAssembler logs conflicts on duplicate widget names."""

    def _make_contributor(
        self, contributor_id: str, widget_names: list[str]
    ) -> MagicMock:
        """Build a mock contributor that returns widgets for the given names."""
        contributor = MagicMock()
        contributor.contributor_id = contributor_id
        contributor.required_permissions = frozenset()
        contributor.get_actions.return_value = []
        contributor.get_navigation_items.return_value = []
        contributor.get_dashboard_widgets.return_value = [
            DashboardWidgetDefinition(
                name=name,
                title=name.replace("_", " ").title(),
                contributor=contributor_id,
                render_endpoint=f"/admin/widgets/{name}",
                view_kind=WidgetKind.STAT,
            )
            for name in widget_names
        ]
        return contributor

    @pytest.mark.asyncio
    async def test_conflict_detection_logs_warning_for_duplicate_widget(self) -> None:
        """A warning is emitted when two contributors claim the same widget name."""
        c1 = self._make_contributor("plugin_a", ["stats_card"])
        c2 = self._make_contributor("plugin_b", ["stats_card"])  # same name!
        assembler = DashboardAssembler(contributors=[c1, c2])

        with structlog.testing.capture_logs() as captured:
            widgets = await assembler.get_all_widgets()

        conflict_logs = [
            log for log in captured if log.get("event") == "admin_widget_conflict"
        ]
        assert conflict_logs, "Expected at least one admin_widget_conflict log entry"
        assert conflict_logs[0]["widget_name"] == "stats_card"
        assert conflict_logs[0]["first_contributor"] == "plugin_a"
        assert conflict_logs[0]["second_contributor"] == "plugin_b"
        # Last writer wins — exactly one widget with that name
        assert len([w for w in widgets if w.name == "stats_card"]) == 1

    @pytest.mark.asyncio
    async def test_no_conflict_when_names_are_unique(self) -> None:
        """No conflict log is emitted when all widget names are distinct."""
        c1 = self._make_contributor("plugin_a", ["widget_a"])
        c2 = self._make_contributor("plugin_b", ["widget_b"])
        assembler = DashboardAssembler(contributors=[c1, c2])

        with structlog.testing.capture_logs() as captured:
            await assembler.get_all_widgets()

        conflict_logs = [
            log for log in captured if log.get("event") == "admin_widget_conflict"
        ]
        assert not conflict_logs


from lexigram.admin.di.sub_providers.contributor import AdminContributorSubProvider
from lexigram.contracts.core.health import HealthStatus


class TestBootFailureTracking:
    @pytest.mark.asyncio
    async def test_boot_failure_does_not_abort_remaining_contributors(self) -> None:
        good = MagicMock()
        good.contributor_id = "good"
        good.on_admin_boot = AsyncMock()

        bad = MagicMock()
        bad.contributor_id = "bad"
        bad.on_admin_boot = AsyncMock(side_effect=RuntimeError("boom"))

        provider = AdminContributorSubProvider(contributors=[good, bad])
        await provider.boot_all()  # must not raise

        good.on_admin_boot.assert_awaited_once()
        bad.on_admin_boot.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_health_check_returns_degraded_when_boot_failures(self) -> None:
        bad = MagicMock()
        bad.contributor_id = "bad"
        bad.on_admin_boot = AsyncMock(side_effect=RuntimeError("boom"))

        provider = AdminContributorSubProvider(contributors=[bad])
        await provider.boot_all()

        result = provider.health_check()
        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_when_no_failures(self) -> None:
        good = MagicMock()
        good.contributor_id = "good"
        good.on_admin_boot = AsyncMock()

        provider = AdminContributorSubProvider(contributors=[good])
        await provider.boot_all()

        result = provider.health_check()
        assert result.status == HealthStatus.HEALTHY
