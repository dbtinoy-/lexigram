from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Literal

from lexigram.admin.config import (
    AdminConfig,
    AdminFeaturesConfig,
    AdminNavigationGroup,
)
from lexigram.primitives.builder import BaseBuilder  # type: ignore[attr-defined]

if TYPE_CHECKING:
    from lexigram.admin.di.bundle_provider import AdminProvider


class AdminBuilder(BaseBuilder["AdminProvider"]):
    """Fluent builder for AdminProvider."""

    def __init__(self) -> None:
        super().__init__()
        self._title: str = "Admin"
        self._prefix: str = "/admin"
        self._require_auth: bool = True
        self._theme: Literal["light", "dark", "system"] = "system"
        self._debug: bool = False
        self._features: dict[str, Any] = {}
        self._extensions: dict[str, dict[str, Any]] = {}
        self._resources: list[Any] = []
        self._controllers: list[Any] = []
        self._navigation_groups: dict[str, AdminNavigationGroup] = {}
        self._commands: list[Any] = []
        self._service_factories: dict[type, Callable[..., Any]] = {}
        self._base_config: AdminConfig | None = None

    @classmethod
    def create(cls) -> AdminBuilder:
        return cls()

    @classmethod
    def from_config(cls, config: AdminConfig) -> AdminBuilder:
        builder = cls()
        builder._title = config.title
        builder._prefix = config.prefix
        builder._require_auth = config.require_auth
        builder._debug = config.debug
        builder._theme = config.ui.theme

        if config.features:
            builder._features = config.features.model_dump()

        builder._navigation_groups = dict(config.navigation_groups)
        builder._commands = list(config.commands)
        builder._extensions = dict(config.extensions) if config.extensions else {}
        builder._base_config = config

        return builder

    def title(self, title: str) -> AdminBuilder:
        self._title = title
        return self

    def prefix(self, prefix: str) -> AdminBuilder:
        self._prefix = prefix
        return self

    def require_auth(self, require: bool) -> AdminBuilder:
        self._require_auth = require
        return self

    def theme(self, theme: Literal["light", "dark", "system"]) -> AdminBuilder:
        self._theme = theme
        return self

    def debug(self, enabled: bool = True) -> AdminBuilder:
        self._debug = enabled
        return self

    def features(self, features: dict[str, Any]) -> AdminBuilder:
        self._features.update(features)
        return self

    def feature(self, name: str, enabled: bool = True) -> AdminBuilder:
        self._features[name] = enabled
        return self

    def extension(
        self,
        name: str,
        enabled: bool = True,
        **options: Any,
    ) -> AdminBuilder:
        self._extensions[name] = {"enabled": enabled, **options}
        return self

    def resources(self, resources: Sequence[Any]) -> AdminBuilder:
        self._resources.extend(resources)
        return self

    def resource(
        self,
        resource: Any,
        *,
        name: str | None = None,
        group: str | None = None,
    ) -> AdminBuilder:
        self._resources.append((resource, name, group))
        return self

    def controllers(self, controllers: Sequence[Any]) -> AdminBuilder:
        self._controllers.extend(controllers)
        return self

    def controller(self, controller: Any) -> AdminBuilder:
        self._controllers.append(controller)
        return self

    def navigation_groups(
        self,
        groups: dict[str, AdminNavigationGroup],
    ) -> AdminBuilder:
        self._navigation_groups.update(groups)
        return self

    def navigation_group(
        self,
        name: str,
        group: AdminNavigationGroup,
    ) -> AdminBuilder:
        self._navigation_groups[name] = group
        return self

    def commands(self, commands: Sequence[Any]) -> AdminBuilder:
        self._commands.extend(commands)
        return self

    def command(
        self,
        label: str,
        href: str,
        *,
        icon: str = "",
        shortcut: str = "",
    ) -> AdminBuilder:
        self._commands.append(
            {"label": label, "href": href, "icon": icon, "shortcut": shortcut},
        )
        return self

    def service(
        self,
        service_type: type,
        factory: Callable[..., Any],
    ) -> AdminBuilder:
        self._service_factories[service_type] = factory
        return self

    def build(self) -> AdminProvider:
        from lexigram.admin.di.bundle_provider import AdminProvider

        if self._base_config is not None:
            config = self._base_config.model_copy(deep=True)
            config.title = self._title
            config.prefix = self._prefix
            config.require_auth = self._require_auth
            config.debug = self._debug
        else:
            features_config = AdminFeaturesConfig(**self._features)
            config_data: dict[str, Any] = {
                "title": self._title,
                "prefix": self._prefix,
                "require_auth": self._require_auth,
                "debug": self._debug,
                "features": features_config,
                "ui": {"theme": self._theme},
            }
            if self._extensions:
                config_data["extensions"] = self._extensions
            config = AdminConfig.model_validate(config_data)

        for name, group in self._navigation_groups.items():
            config.navigation_groups[name] = group

        for cmd in self._commands:
            if isinstance(cmd, dict):
                from lexigram.admin.models.provider_models import Command

                config.commands.append(
                    Command(
                        label=cmd.get("label", ""),
                        href=cmd.get("href", ""),
                        icon=cmd.get("icon", ""),
                        shortcut=cmd.get("shortcut", ""),
                    )
                )
            else:
                config.commands.append(cmd)

        resources_list = []
        for res in self._resources:
            if isinstance(res, tuple):
                resource, name, group = res
                resources_list.append(resource)
            else:
                resources_list.append(res)

        return AdminProvider(
            config=config,
            resources=resources_list,
            controllers=list(self._controllers),
        )
