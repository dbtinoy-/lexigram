"""ModuleScanner — discover BaseSkill and FunctionSkill instances in Python modules."""

from __future__ import annotations

import importlib
import types
from typing import TYPE_CHECKING

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.skills.registry import SkillRegistry
    from lexigram.contracts.core.di import ContainerProtocol

logger = get_logger(__name__)


class ModuleScanner:
    """Discover and auto-register skills from Python modules.

    The scanner walks every attribute of the target module.  Attributes that
    are instances of :class:`BaseSkill` (or its subclasses, including
    :class:`FunctionSkill`) are registered into the provided
    :class:`SkillRegistry`.

    Example::

        scanner = ModuleScanner(container)
        await scanner.scan(registry, "myapp.skills.builtin")
    """

    def __init__(self, container: ContainerProtocol | None = None) -> None:
        """Initialise the scanner.

        Args:
            container: Optional DI container for resolving class-based skills.
        """
        self._container = container

    async def scan(self, registry: SkillRegistry, module_path: str) -> int:
        """Import *module_path* and register all discovered skills.

        Args:
            registry: The :class:`SkillRegistry` to register discovered skills
                into.
            module_path: Dotted import path of the module to scan.

        Returns:
            Number of skills successfully registered.
        """
        from lexigram.ai.skills.base import BaseSkill

        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            logger.error(
                "module_scanner_import_error",
                module=module_path,
                error=str(exc),
            )
            raise

        registered = 0
        for name in dir(module):
            obj = getattr(module, name, None)
            if obj is None:
                continue
            if isinstance(obj, BaseSkill):
                try:
                    registry.register(obj)
                    registered += 1
                    logger.debug(
                        "module_scanner_registered_instance",
                        skill=obj.definition.name,
                        module=module_path,
                    )
                except Exception as exc:  # noqa: BLE001 — best-effort scan
                    logger.warning(
                        "module_scanner_register_error",
                        skill=name,
                        error=str(exc),
                    )
            elif (
                isinstance(obj, type)
                and issubclass(obj, BaseSkill)
                and obj is not BaseSkill
                and self._container is not None
            ):
                try:
                    # Instantiate via DI container
                    instance = await self._container.resolve(obj)
                    if isinstance(instance, BaseSkill):
                        registry.register(instance)
                        registered += 1
                        logger.debug(
                            "module_scanner_registered_class",
                            skill=instance.definition.name,
                            module=module_path,
                            cls=obj.__name__,
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "module_scanner_di_resolve_error",
                        cls=obj.__name__,
                        module=module_path,
                        error=str(exc),
                    )

        logger.info(
            "module_scanner_complete",
            module=module_path,
            registered=registered,
        )
        return registered

    async def scan_package(self, registry: SkillRegistry, package_path: str) -> int:
        """Recursively scan all modules within a package.

        Args:
            registry: The :class:`SkillRegistry` to register discovered skills
                into.
            package_path: Dotted import path of the package to scan.

        Returns:
            Total number of skills registered across all sub-modules.
        """
        import pkgutil

        try:
            package = importlib.import_module(package_path)
        except ImportError as exc:
            logger.error(
                "module_scanner_package_error",
                package=package_path,
                error=str(exc),
            )
            raise

        total = 0
        prefix = package.__name__ + "."

        if not isinstance(package, types.ModuleType):
            return total

        pkg_path = getattr(package, "__path__", None)
        if pkg_path is None:
            return total

        for module_info in pkgutil.walk_packages(pkg_path, prefix=prefix):
            if not module_info.ispkg:
                total += await self.scan(registry, module_info.name)

        return total
