"""Health check plugin modules, grouped by domain cluster."""

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

__all__ = [
    "CheckResult",
    "CheckStatus",
    "ConfigFileCheck",
    "CrossExtensionImportCheck",
    "DependenciesCheck",
    "DockerCheck",
    "GitCheck",
    "HealthCheck",
    "InstalledLexigramPackagesCheck",
    "PackageManagerCheck",
    "ProjectStructureCheck",
    "ProviderPackagesCheck",
    "PythonVersionCheck",
    "RequiredToolsCheck",
]
