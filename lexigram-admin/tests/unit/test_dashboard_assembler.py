"""Tests for DashboardAssembler."""

from __future__ import annotations

import pytest

from lexigram.admin.contributors.base import BaseAdminContributor
from lexigram.admin.dashboard.assembler import DashboardAssembler
from lexigram.contracts.admin.protocols import AdminDashboardProtocol
from lexigram.contracts.admin.types import (
    AdminActionDefinition,
    AdminHealthDefinition,
    DashboardWidgetDefinition,
    NavigationContribution,
    WidgetCategory,
    WidgetSize,
)


class CacheContributor(BaseAdminContributor):
    name = "cache"
    display_name = "Cache"
    group = "infrastructure"
    icon = "database"
    priority = 30

    def get_dashboard_widgets(self):
        return [
            DashboardWidgetDefinition(
                name="cache_hit_rate",
                title="Cache Hit Rate",
                contributor="cache",
                render_endpoint="/admin/contrib/cache/widgets/hit-rate",
                size=WidgetSize.SMALL,
                category=WidgetCategory.METRICS,
                order=10,
            ),
        ]

    def get_navigation_items(self):
        return [
            NavigationContribution(
                label="Cache",
                url="/admin/framework/cache",
                icon="database",
                group="infrastructure",
                order=30,
            ),
        ]

    def get_health_definitions(self):
        return [
            AdminHealthDefinition(
                name="cache_backend",
                contributor="cache",
                component="Cache Backend",
            ),
        ]

    def get_actions(self):
        return [
            AdminActionDefinition(
                name="flush_cache",
                title="Flush",
                contributor="cache",
                handler="mod:func",
                destructive=True,
            ),
        ]


class EventsContributor(BaseAdminContributor):
    name = "events"
    display_name = "Events"
    group = "infrastructure"
    icon = "radio"
    priority = 40

    def get_dashboard_widgets(self):
        return [
            DashboardWidgetDefinition(
                name="event_throughput",
                title="Event Throughput",
                contributor="events",
                render_endpoint="/admin/contrib/events/widgets/throughput",
                size=WidgetSize.SMALL,
                category=WidgetCategory.METRICS,
                order=20,
            ),
        ]


class TestDashboardAssembler:
    def _make_assembler(self) -> DashboardAssembler:
        return DashboardAssembler(
            contributors=[CacheContributor(), EventsContributor()]
        )

    def test_implements_protocol(self) -> None:
        assembler = self._make_assembler()
        assert isinstance(assembler, AdminDashboardProtocol)

    @pytest.mark.asyncio
    async def test_get_all_widgets(self) -> None:
        assembler = self._make_assembler()
        widgets = await assembler.get_all_widgets()
        assert len(widgets) == 2
        names = [w.name for w in widgets]
        assert "cache_hit_rate" in names
        assert "event_throughput" in names

    @pytest.mark.asyncio
    async def test_widgets_sorted_by_category_then_order(self) -> None:
        assembler = self._make_assembler()
        widgets = await assembler.get_all_widgets()
        orders = [(w.category.value, w.order) for w in widgets]
        assert orders == sorted(orders)

    @pytest.mark.asyncio
    async def test_get_all_navigation(self) -> None:
        assembler = self._make_assembler()
        nav = await assembler.get_all_navigation()
        assert len(nav) >= 1
        labels = [n.label for n in nav]
        assert "Cache" in labels

    @pytest.mark.asyncio
    async def test_navigation_sorted_by_group_then_order(self) -> None:
        assembler = self._make_assembler()
        nav = await assembler.get_all_navigation()
        keys = [(n.group, n.order) for n in nav]
        assert keys == sorted(keys)

    @pytest.mark.asyncio
    async def test_get_framework_health(self) -> None:
        assembler = self._make_assembler()
        health = await assembler.get_framework_health()
        assert "cache_backend" in health

    @pytest.mark.asyncio
    async def test_get_all_actions(self) -> None:
        assembler = self._make_assembler()
        actions = await assembler.get_all_actions()
        assert len(actions) == 1
        assert actions[0].name == "flush_cache"
