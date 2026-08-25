"""Health check registry for system diagnostics.

This module provides a registry pattern for running various health checks
on the system, configuration, and dependencies. The check implementations
live in the ``health_checks`` package (one module per domain cluster) and
are re-exported here so the public surface of this module is unchanged.
"""

from __future__ import annotations

from lexigram.cli.registry.health_checks.base import (
    CheckResult as CheckResult,
)
from lexigram.cli.registry.health_checks.base import (
    CheckStatus as CheckStatus,
)
from lexigram.cli.registry.health_checks.base import (
    HealthCheck as HealthCheck,
)
from lexigram.cli.registry.health_checks.deps import (
    InstalledLexigramPackagesCheck as InstalledLexigramPackagesCheck,
)
from lexigram.cli.registry.health_checks.project import (
    ConfigFileCheck as ConfigFileCheck,
)
from lexigram.cli.registry.health_checks.project import (
    DependenciesCheck as DependenciesCheck,
)
from lexigram.cli.registry.health_checks.project import (
    ProjectStructureCheck as ProjectStructureCheck,
)
from lexigram.cli.registry.health_checks.providers import (
    CrossExtensionImportCheck as CrossExtensionImportCheck,
)
from lexigram.cli.registry.health_checks.providers import (
    ProviderPackagesCheck as ProviderPackagesCheck,
)
from lexigram.cli.registry.health_checks.python_env import (
    PythonVersionCheck as PythonVersionCheck,
)
from lexigram.cli.registry.health_checks.tools import (
    PackageManagerCheck as PackageManagerCheck,
)
from lexigram.cli.registry.health_checks.tools import (
    RequiredToolsCheck as RequiredToolsCheck,
)
from lexigram.cli.registry.health_checks.vcs_docker import (
    DockerCheck as DockerCheck,
)
from lexigram.cli.registry.health_checks.vcs_docker import (
    GitCheck as GitCheck,
)


class HealthCheckRegistry:
    """Registry for health checks.

    Provides a pluggable way to add new health checks.
    """

    _checks: list[type[HealthCheck]] = []
    _initialized: bool = False

    @classmethod
    def register(cls, check: type[HealthCheck]) -> None:
        """Register a health check class."""
        cls._checks.append(check)

    @classmethod
    def get_all_checks(cls) -> list[type[HealthCheck]]:
        """Get all registered health check classes."""
        cls.register_defaults()
        return cls._checks.copy()

    @classmethod
    def get_checks_by_category(cls) -> dict[str, list[HealthCheck]]:
        """Get all checks organized by category."""
        checks = cls.get_all_checks()
        by_category: dict[str, list[HealthCheck]] = {}

        for check_class in checks:
            instance = check_class()
            category = instance.get_category()
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(instance)

        return by_category

    @classmethod
    def register_defaults(cls) -> None:
        """Initialize default checks if not already done."""
        if not cls._initialized:
            cls.register(PythonVersionCheck)
            cls.register(PackageManagerCheck)
            cls.register(RequiredToolsCheck)
            cls.register(ConfigFileCheck)
            cls.register(ProjectStructureCheck)
            cls.register(DependenciesCheck)
            cls.register(GitCheck)
            cls.register(DockerCheck)
            # Framework-specific checks (Dim 9.4)
            cls.register(InstalledLexigramPackagesCheck)
            cls.register(ProviderPackagesCheck)
            cls.register(CrossExtensionImportCheck)
            cls._initialized = True


def run_health_checks() -> dict[str, list[CheckResult]]:
    """Run all health checks and return results organized by category."""
    by_category = HealthCheckRegistry.get_checks_by_category()
    results: dict[str, list[CheckResult]] = {}

    for category, checks in by_category.items():
        results[category] = []
        for check in checks:
            try:
                result = check.check()
            except (RuntimeError, OSError, AttributeError, LookupError) as e:
                result = CheckResult(
                    name=check.get_name(),
                    status=CheckStatus.FAIL,
                    message=f"Check failed with error: {e}",
                )
            results[category].append(result)

    return results


__all__ = [
    "CheckResult",
    "CheckStatus",
    "ConfigFileCheck",
    "CrossExtensionImportCheck",
    "DependenciesCheck",
    "DockerCheck",
    "GitCheck",
    "HealthCheck",
    "HealthCheckRegistry",
    "InstalledLexigramPackagesCheck",
    "PackageManagerCheck",
    "ProjectStructureCheck",
    "ProviderPackagesCheck",
    "PythonVersionCheck",
    "RequiredToolsCheck",
    "run_health_checks",
]
