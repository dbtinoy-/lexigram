"""Tests for NavigationAssembler."""
from __future__ import annotations

import pytest

from lexigram.admin.contributors.base import BaseAdminContributor
from lexigram.admin.contributors.registry import ContributorRegistry
from lexigram.admin.navigation.assembler import (
    NavigationAssembler,
    contributions_to_flat_nav,
)
from lexigram.contracts.admin.types import NavigationContribution


class InfraContributor(BaseAdminContributor):
    name = "cache"
    display_name = "Cache"
    group = "infrastructure"
    icon = "database"
    priority = 30

    def get_navigation_items(self):
        return [
            NavigationContribution(
                label="Cache", url="/admin/framework/cache",
                icon="database", group="infrastructure", order=30,
            ),
        ]


class SecurityContributor(BaseAdminContributor):
    name = "auth"
    display_name = "Auth"
    group = "security"
    icon = "shield"
    priority = 20

    def get_navigation_items(self):
        return [
            NavigationContribution(
                label="Auth", url="/admin/framework/auth",
                icon="shield", group="security", order=10,
            ),
        ]


class TestNavigationAssembler:
    def _make_assembler(self) -> NavigationAssembler:
        registry = ContributorRegistry()
        registry.add(InfraContributor())
        registry.add(SecurityContributor())
        return NavigationAssembler(
            contributor_registry=registry,
            resource_items=[],
        )

    @pytest.mark.asyncio
    async def test_build_returns_groups(self) -> None:
        assembler = self._make_assembler()
        groups = await assembler.build()
        assert isinstance(groups, dict)
        assert "infrastructure" in groups
        assert "security" in groups

    @pytest.mark.asyncio
    async def test_build_includes_contributor_nav(self) -> None:
        assembler = self._make_assembler()
        groups = await assembler.build()
        infra_labels = [n.label for n in groups["infrastructure"]]
        assert "Cache" in infra_labels

    @pytest.mark.asyncio
    async def test_build_with_resource_items(self) -> None:
        registry = ContributorRegistry()
        resource_items = [
            NavigationContribution(
                label="Users", url="/admin/resources/users",
                icon="users", group="resources", order=10,
            ),
        ]
        assembler = NavigationAssembler(
            contributor_registry=registry,
            resource_items=resource_items,
        )
        groups = await assembler.build()
        assert "resources" in groups
        assert groups["resources"][0].label == "Users"

    @pytest.mark.asyncio
    async def test_items_sorted_by_order_within_group(self) -> None:
        registry = ContributorRegistry()

        class MultiNav(BaseAdminContributor):
            name = "multi"
            display_name = "Multi"
            group = "test"
            icon = "box"
            priority = 10

            def get_navigation_items(self):
                return [
                    NavigationContribution(label="C", url="/c", group="test", order=30),
                    NavigationContribution(label="A", url="/a", group="test", order=10),
                    NavigationContribution(label="B", url="/b", group="test", order=20),
                ]

        registry.add(MultiNav())
        assembler = NavigationAssembler(contributor_registry=registry, resource_items=[])
        groups = await assembler.build()
        labels = [n.label for n in groups["test"]]
        assert labels == ["A", "B", "C"]


class TestContributionsToFlatNav:
    """Tests for contributions_to_flat_nav converter."""

    def test_converts_contributions_to_flat_dicts(self) -> None:
        groups = {
            "infrastructure": [
                NavigationContribution(
                    label="Cache", url="/admin/cache",
                    icon="database", group="infrastructure",
                ),
            ],
            "catalog": [
                NavigationContribution(
                    label="Vet Clinics", url="/admin/piccolina_catalog.vet_clinics",
                    icon="cross", group="catalog",
                ),
            ],
        }
        result = contributions_to_flat_nav(groups)
        assert len(result) == 4  # 2 group headers + 2 items

        assert result[0] == {"is_group": True, "label": "Catalog"}
        assert result[1] == {
            "label": "Vet Clinics", "href": "/admin/piccolina_catalog.vet_clinics",
            "icon": "cross",
        }
        assert result[2] == {"is_group": True, "label": "Infrastructure"}
        assert result[3] == {
            "label": "Cache", "href": "/admin/cache",
            "icon": "database",
        }

    def test_includes_permission_and_badge_when_present(self) -> None:
        groups = {
            "admin": [
                NavigationContribution(
                    label="Admin Panel", url="/admin/panel",
                    icon="settings", group="admin",
                    permission="admin.read", badge_endpoint="/badges/admin",
                ),
            ],
        }
        result = contributions_to_flat_nav(groups)
        item = result[1]
        assert item["permission"] == "admin.read"
        assert item["badge"] == "/badges/admin"

    def test_empty_groups_returns_empty_list(self) -> None:
        assert contributions_to_flat_nav({}) == []

    def test_group_with_no_items_is_skipped(self) -> None:
        groups = {
            "empty": [],
            "populated": [
                NavigationContribution(
                    label="Something", url="/something",
                    icon="box", group="populated",
                ),
            ],
        }
        result = contributions_to_flat_nav(groups)
        assert result[0] == {"is_group": True, "label": "Populated"}
        assert len(result) == 2  # 1 group header + 1 item
        assert not any(i.get("label") == "Empty" for i in result)
