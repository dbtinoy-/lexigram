"""Integration tests for contributor resource contribution (Phase C)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from lexigram.contracts.admin import BaseAdminContributor


class _DummyResource:
    name = "dummy"
    icon = "box"

    def __init__(self) -> None:
        self.booted = False


class _DummyWithArgs:
    name = "with_args"

    def __init__(self, required_arg: str) -> None:
        pass


class _ContributorWithResource(BaseAdminContributor):
    name = "test_contributor"
    display_name = "Test Contributor"
    group = "test"
    icon = "box"
    priority = 100
    version = "0"
    package_source = "test_pkg"
    required_permissions: frozenset[str] = frozenset()

    def get_resources(self) -> list[type]:
        return [_DummyResource]


class _ContributorWithBadResource(BaseAdminContributor):
    name = "bad_resource"
    display_name = "Bad Resource"
    group = "test"
    icon = "box"
    priority = 100
    version = "0"
    package_source = "bad_pkg"
    required_permissions: frozenset[str] = frozenset()

    def get_resources(self) -> list[type]:
        return [_DummyWithArgs]


class _ContributorEmpty(BaseAdminContributor):
    name = "empty"
    display_name = "Empty"
    group = "test"
    icon = "box"
    priority = 100
    version = "0"
    package_source = "empty_pkg"
    required_permissions: frozenset[str] = frozenset()


class TestContributorResourceContribution:
    def test_contributor_can_return_resource_classes(self) -> None:
        c = _ContributorWithResource()
        resources = c.get_resources()
        assert len(resources) == 1
        assert resources[0] is _DummyResource

    def test_contributor_without_resources_returns_empty(self) -> None:
        c = _ContributorEmpty()
        assert list(c.get_resources()) == []

    async def test_contributor_resource_merged_at_mount_time(self) -> None:
        """mount_to_app merges contributed resources into AdminRouter."""
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.contributors.registry import ContributorRegistry
        from lexigram.admin.core.routing import AdminRouter
        from lexigram.admin.di.bundle_provider import AdminProvider
        from lexigram.di.container import Container

        captured: dict[str, object] = {}

        def fake_init(self: object, **kw: object) -> None:
            if "resources" in kw:
                captured.update(kw["resources"])
            self._resources = kw.get("resources", {})
            self._controllers = kw.get("controllers", [])
            self._middleware_stack = kw.get("middleware_stack", [])
            self._is_mounted = False

        with patch.object(AdminRouter, "__init__", fake_init):
            with patch.object(AdminRouter, "mount", return_value=None):
                config = AdminConfig.from_dict(
                    {"auth": {"security": {"setup_token": "test-setup-token"}}}
                )
                bundle = AdminProvider(config=config)
                container = Container()
                from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
                container.singleton(DatabaseProviderProtocol, lambda: MagicMock())
                await bundle.register(container)

                registry = await container.resolve(
                    ContributorRegistry, bypass_visibility=True
                )
                registry.register(_ContributorWithResource())
                await bundle.boot(container)

                mock_app = MagicMock()
                mock_app.state = MagicMock()
                await bundle.mount_to_app(mock_app, container)

        assert "test_pkg.dummy" in captured

    async def test_unresolvable_resource_skipped_gracefully(self) -> None:
        """Resources that can't be instantiated are silently skipped."""
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.contributors.registry import ContributorRegistry
        from lexigram.admin.core.routing import AdminRouter
        from lexigram.admin.di.bundle_provider import AdminProvider
        from lexigram.di.container import Container

        captured: dict[str, object] = {}

        def fake_init(self: object, **kw: object) -> None:
            if "resources" in kw:
                captured.update(kw["resources"])
            self._resources = kw.get("resources", {})
            self._controllers = kw.get("controllers", [])
            self._middleware_stack = kw.get("middleware_stack", [])
            self._is_mounted = False

        with patch.object(AdminRouter, "__init__", fake_init):
            with patch.object(AdminRouter, "mount", return_value=None):
                config = AdminConfig.from_dict(
                    {"auth": {"security": {"setup_token": "test-setup-token"}}}
                )
                bundle = AdminProvider(config=config)
                container = Container()
                from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
                container.singleton(DatabaseProviderProtocol, lambda: MagicMock())
                await bundle.register(container)

                registry = await container.resolve(
                    ContributorRegistry, bypass_visibility=True
                )
                registry.register(_ContributorWithBadResource())
                await bundle.boot(container)

                mock_app = MagicMock()
                mock_app.state = MagicMock()
                await bundle.mount_to_app(mock_app, container)

        assert "with_args" not in captured
