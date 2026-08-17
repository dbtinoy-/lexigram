from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import TYPE_CHECKING, Any, Self

from lexigram.admin.config import AdminConfig
from lexigram.admin.models.provider_models import Command
from lexigram.contracts.exceptions import ConfigurationError
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.resources.base import Resource
    from lexigram.contracts.core.di import ContainerRegistrarProtocol

logger = get_logger(__name__)


class AdminRegistry:
    """Standalone registry for admin resources and controllers."""

    def __init__(self, config: AdminConfig | None = None):
        self._config = config
        self._resources: dict[str, Any] = {}
        self._deferred_resources: dict[str, type] = {}
        self._controllers: list[Any] = []
        self._commands: list[Command] = []
        self._mounted: bool = False

    @property
    def resources(self) -> dict[str, Any]:
        return self._resources

    @property
    def controllers(self) -> list[Any]:
        return self._controllers

    @property
    def commands(self) -> list[Command]:
        return self._commands

    def register_resource(
        self,
        resource: type | Resource,
        *,
        name: str | None = None,
        group: str | None = None,
    ) -> Self:
        if self._mounted:
            raise ConfigurationError(message="Cannot register resources after mounting")

        is_class = isinstance(resource, type)
        resource_name = name or self._extract_resource_name(resource, is_class)
        resource_group = group or self._extract_resource_group(resource, is_class)

        if is_class:
            self._deferred_resources[resource_name] = resource  # type: ignore[assignment]
            logger.debug("Deferred resource registration: %s", resource_name)
        else:
            self._resources[resource_name] = resource
            logger.debug("Registered resource: %s", resource_name)

        if resource_group:
            self._assign_resource_to_group(
                resource_name, resource_group, resource, is_class
            )

        return self

    @staticmethod
    def _extract_resource_name(resource: type | Any, is_class: bool) -> str:
        name = getattr(resource, "name", None)
        if not name:
            cfg = getattr(resource, "config", None)
            if cfg is not None:
                name = getattr(cfg, "_name", None)
        if not name:
            cls = resource if is_class else resource.__class__
            name = cls.__name__.lower().replace("resource", "")
        return name

    @staticmethod
    def _extract_resource_group(resource: type | Any, _is_class: bool) -> str | None:
        group = getattr(resource, "group", None)
        if not group:
            cfg = getattr(resource, "config", None)
            if cfg is not None:
                group = getattr(cfg, "_group", None)
        return group

    def _assign_resource_to_group(
        self,
        resource_name: str,
        group_key: str,
        resource: type | Any,
        is_class: bool,
    ) -> None:
        nav_groups = self._config.navigation_groups if self._config else {}

        if group_key not in nav_groups:
            cfg = getattr(resource, "config", None)
            group_label = None
            group_icon = None
            group_order = 100
            if cfg is not None:
                group_label = getattr(cfg, "_group_label", None)
                group_icon = getattr(cfg, "_group_icon", None)
                group_order = getattr(cfg, "_group_order", None) or 100

            from lexigram.admin.config import AdminNavigationGroup

            nav_groups[group_key] = AdminNavigationGroup(
                label=group_label or group_key.replace("_", " ").title(),
                icon=group_icon,
                order=group_order,
            )
            logger.debug("Auto-created navigation group: %s", group_key)

        nav_group = nav_groups[group_key]
        if resource_name not in nav_group.resources:
            nav_group.resources.append(resource_name)

    def register_many(self, *resources: type | Resource) -> Self:
        for resource in resources:
            self.register_resource(resource)
        return self

    def register_command(self, command: Any) -> Self:
        if isinstance(command, dict):
            cmd = Command(
                label=command.get("label", ""),
                href=command.get("href", ""),
                icon=command.get("icon", ""),
                shortcut=command.get("shortcut", ""),
            )
        elif hasattr(command, "label"):
            cmd = Command(
                label=getattr(command, "label", ""),
                href=getattr(command, "href", ""),
                icon=getattr(command, "icon", ""),
                shortcut=getattr(command, "shortcut", ""),
            )
        else:
            raise ValueError(f"Invalid command type: {type(command)}")

        self._commands.append(cmd)
        return self

    def register_controller(self, controller: type | Any) -> Self:
        if self._mounted:
            raise ConfigurationError(
                message="Cannot register controllers after mounting",
            )

        self._controllers.append(controller)
        logger.debug(
            "Registered controller: %s",
            getattr(controller, "__name__", str(controller)),
        )
        return self

    def discover_resources(
        self,
        package: str,
        container: ContainerRegistrarProtocol,
    ) -> Self:
        from lexigram.admin.resources.base import Resource

        count = 0
        for cls in self._scan_package(package, Resource):
            container.transient(cls, cls)
            self.register_resource(cls)
            count += 1

        logger.info("Discovered %d admin resources in %s", count, package)
        return self

    def discover_controllers(
        self,
        package: str,
        container: ContainerRegistrarProtocol,
    ) -> Self:
        from lexigram.admin.controllers import AdminController

        count = 0
        for cls in self._scan_package(package, AdminController):
            self.register_controller(cls)
            count += 1

        logger.info("Discovered %d admin controllers in %s", count, package)
        return self

    @staticmethod
    def _scan_package(package: str, base_class: type) -> list[type]:
        found: list[type] = []
        seen: set[type] = set()

        mod = importlib.import_module(package)
        pkg_path = getattr(mod, "__path__", None)
        if pkg_path is None:
            return found

        for _importer, modname, _ispkg in pkgutil.walk_packages(
            pkg_path, prefix=package + "."
        ):
            try:
                submod = importlib.import_module(modname)
            except (ImportError, ModuleNotFoundError, AttributeError, TypeError) as exc:
                logger.debug("Skipping unimportable module: %s (%s)", modname, exc)
                continue

            for attr_name in dir(submod):
                obj = getattr(submod, attr_name, None)
                if (
                    obj is not None
                    and inspect.isclass(obj)
                    and issubclass(obj, base_class)
                    and obj is not base_class
                    and not inspect.isabstract(obj)
                    and obj not in seen
                ):
                    seen.add(obj)
                    found.append(obj)

        return found
