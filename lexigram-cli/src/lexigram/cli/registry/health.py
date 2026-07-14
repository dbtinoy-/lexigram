"""Health check registry for system diagnostics.

This module provides a registry pattern for running various health checks
on the system, configuration, and dependencies.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from importlib.metadata import PackageNotFoundError, distribution, distributions
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from lexigram.logging import get_logger

logger = get_logger(__name__)


class CheckStatus(str, Enum):
    """Status of a health check."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CheckResult:
    """Result of a health check."""

    name: str
    status: CheckStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def icon(self) -> str:
        """Get icon for status."""
        return {
            CheckStatus.PASS: "✓",
            CheckStatus.WARNING: "⚠",
            CheckStatus.FAIL: "✗",
            CheckStatus.SKIP: "○",
        }.get(self.status, "?")

    @property
    def color(self) -> str:
        """Get color for status."""
        return {
            CheckStatus.PASS: "success",
            CheckStatus.WARNING: "warning",
            CheckStatus.FAIL: "error",
            CheckStatus.SKIP: "dim",
        }.get(self.status, "")


class HealthCheck(abc.ABC):
    """Abstract base class for health checks."""

    @abc.abstractmethod
    def check(self) -> CheckResult:
        """Run the health check and return the result."""

    @abc.abstractmethod
    def get_name(self) -> str:
        """Get the name of this check."""

    def get_category(self) -> str:
        """Get the category for this check (for grouping)."""
        return "General"


class PythonVersionCheck(HealthCheck):
    """Check if Python version meets minimum requirements."""

    MIN_VERSION = (3, 11)

    def get_name(self) -> str:
        return "Python Version"

    def get_category(self) -> str:
        return "Runtime"

    def check(self) -> CheckResult:
        version = sys.version_info
        meets_min = (
            version.major >= self.MIN_VERSION[0]
            and version.minor >= self.MIN_VERSION[1]
        )

        if meets_min:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.PASS,
                message=f"Python {version.major}.{version.minor}.{version.micro}",
            )
        return CheckResult(
            name=self.get_name(),
            status=CheckStatus.FAIL,
            message=f"Python {version.major}.{version.minor} (minimum {self.MIN_VERSION[0]}.{self.MIN_VERSION[1]} required)",
        )


class PackageManagerCheck(HealthCheck):
    """Check if uv package manager is available."""

    def get_name(self) -> str:
        return "Package Manager"

    def get_category(self) -> str:
        return "Tools"

    def check(self) -> CheckResult:
        uv_path = shutil.which("uv")
        if uv_path:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.PASS,
                message=f"uv found at {uv_path}",
            )
        return CheckResult(
            name=self.get_name(),
            status=CheckStatus.FAIL,
            message="uv not installed",
        )


class RequiredToolsCheck(HealthCheck):
    """Check if required development tools are installed."""

    TOOLS = ["pytest", "ruff", "mypy"]

    def get_name(self) -> str:
        return "Required Tools"

    def get_category(self) -> str:
        return "Tools"

    def check(self) -> CheckResult:
        missing = []
        found = []

        for tool in self.TOOLS:
            if shutil.which(tool):
                found.append(tool)
            else:
                missing.append(tool)

        if not missing:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.PASS,
                message=f"All required tools available: {', '.join(found)}",
            )
        if found:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.WARNING,
                message=f"Missing tools: {', '.join(missing)}",
            )
        return CheckResult(
            name=self.get_name(),
            status=CheckStatus.FAIL,
            message=f"No tools found. Required: {', '.join(self.TOOLS)}",
        )


class ConfigFileCheck(HealthCheck):
    """Check if application.yaml exists and is valid."""

    def get_name(self) -> str:
        return "Configuration File"

    def get_category(self) -> str:
        return "Project"

    def check(self) -> CheckResult:
        config_path = Path("application.yaml")

        if not config_path.exists():
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.FAIL,
                message="application.yaml not found",
            )

        try:
            import yaml

            with open(config_path) as f:
                yaml.safe_load(f)
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.PASS,
                message="application.yaml found and valid",
            )
        except yaml.YAMLError as e:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.FAIL,
                message=f"Invalid YAML: {e}",
            )
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.FAIL,
                message=f"Error: {e}",
            )


class ProjectStructureCheck(HealthCheck):
    """Check if required project directories exist."""

    REQUIRED_PATHS = [
        ("src/", "Source directory"),
        ("pyproject.toml", "Project file"),
    ]

    def get_name(self) -> str:
        return "Project Structure"

    def get_category(self) -> str:
        return "Project"

    def check(self) -> CheckResult:
        missing = []
        found = []

        for path, desc in self.REQUIRED_PATHS:
            p = Path(path)
            if p.exists():
                found.append(desc)
            else:
                missing.append(desc)

        if not missing:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.PASS,
                message=f"All required paths exist: {', '.join(found)}",
            )
        return CheckResult(
            name=self.get_name(),
            status=CheckStatus.WARNING,
            message=f"Missing: {', '.join(missing)}",
        )


class DependenciesCheck(HealthCheck):
    """Check if project dependencies are installed."""

    def get_name(self) -> str:
        return "Dependencies"

    def get_category(self) -> str:
        return "Project"

    def check(self) -> CheckResult:
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.FAIL,
                message="pyproject.toml not found",
            )

        if Path("node_modules").exists() or any(Path().glob("*.egg-info")):
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.PASS,
                message="Dependencies appear to be installed",
            )

        uv_lock = Path("uv.lock")
        if uv_lock.exists():
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.WARNING,
                message="uv.lock exists but dependencies may not be installed",
            )

        return CheckResult(
            name=self.get_name(),
            status=CheckStatus.WARNING,
            message="Run 'uv sync' to install dependencies",
        )


class GitCheck(HealthCheck):
    """Check if git is initialized."""

    def get_name(self) -> str:
        return "Git"

    def get_category(self) -> str:
        return "Version Control"

    def check(self) -> CheckResult:
        git_path = shutil.which("git")
        if not git_path:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.SKIP,
                message="git not installed",
            )

        git_dir = Path(".git")
        if git_dir.exists():
            try:
                result = subprocess.run(
                    ["git", "status"],  # noqa: S607 — static CLI tool on PATH (operator-invoked)
                    capture_output=True,
                    check=False,
                )
                if result.returncode == 0:
                    return CheckResult(
                        name=self.get_name(),
                        status=CheckStatus.PASS,
                        message="Git repository initialized",
                    )
            except (RuntimeError, OSError, AttributeError, LookupError) as exc:
                logger.debug("git_check_failed", error=str(exc))

        return CheckResult(
            name=self.get_name(),
            status=CheckStatus.WARNING,
            message="Not a git repository",
        )


class DockerCheck(HealthCheck):
    """Check if Docker is available."""

    def get_name(self) -> str:
        return "Docker"

    def get_category(self) -> str:
        return "Container"

    def check(self) -> CheckResult:
        docker_path = shutil.which("docker")
        if not docker_path:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.SKIP,
                message="Docker not installed (optional)",
            )

        try:
            result = subprocess.run(
                ["docker", "version"],  # noqa: S607 — static CLI tool on PATH (operator-invoked)
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                return CheckResult(
                    name=self.get_name(),
                    status=CheckStatus.PASS,
                    message="Docker available",
                )
        except (RuntimeError, OSError, AttributeError, LookupError) as exc:
            logger.debug("docker_check_failed", error=str(exc))

        return CheckResult(
            name=self.get_name(),
            status=CheckStatus.WARNING,
            message="Docker installed but not running",
        )


# ---------------------------------------------------------------------------
# Framework-specific checks (added by Dim 9.4 expansion)
# ---------------------------------------------------------------------------

#: Maps application.yaml provider keys to the package that implements them.
_PROVIDER_PACKAGES: dict[str, str] = {
    "ai": "lexigram-ai",
    "auth": "lexigram-auth",
    "cache": "lexigram-cache",
    "database": "lexigram-sql",
    "events": "lexigram-events",
    "graphql": "lexigram-graphql",
    "queue": "lexigram-queue",
    "mailer": "lexigram-notification",
    "notification": "lexigram-notification",
    "monitor": "lexigram-monitor",
    "search": "lexigram-search",
    "storage": "lexigram-storage",
    "tasks": "lexigram-tasks",
    "web": "lexigram-web",
}


class InstalledLexigramPackagesCheck(HealthCheck):
    """Report all installed lexigram-* packages and their versions."""

    def get_name(self) -> str:
        """Return the display name of this check."""
        return "Installed Packages"

    def get_category(self) -> str:
        """Return the grouping category for this check."""
        return "Framework"

    def check(self) -> CheckResult:
        """Scan the active environment for installed lexigram-* distributions."""
        pkgs: dict[str, str] = {}
        for dist in distributions():
            name: str = dist.metadata["Name"] if dist.metadata.get("Name") else ""  # type: ignore[attr-defined]
            if name.startswith("lexigram"):
                version: str = (
                    dist.metadata["Version"] if "Version" in dist.metadata else "?"  # noqa: SIM401
                )
                pkgs[name] = version

        if pkgs:
            pkg_list = ", ".join(f"{n}=={v}" for n, v in sorted(pkgs.items()))
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.PASS,
                message=f"{len(pkgs)} package(s): {pkg_list}",
                details={"packages": pkgs},
            )
        return CheckResult(
            name=self.get_name(),
            status=CheckStatus.WARNING,
            message="No lexigram-* packages found in active environment",
        )


class ProviderPackagesCheck(HealthCheck):
    """Verify that each provider declared in application.yaml has its package installed."""

    def get_name(self) -> str:
        """Return the display name of this check."""
        return "Provider Packages"

    def get_category(self) -> str:
        """Return the grouping category for this check."""
        return "Framework"

    def check(self) -> CheckResult:
        """Cross-reference application.yaml providers with installed distributions."""
        config_path = Path("application.yaml")
        if not config_path.exists():
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.SKIP,
                message="application.yaml not found — no providers to check",
            )

        try:
            import yaml

            with open(config_path) as f:
                config: dict[str, Any] = yaml.safe_load(f) or {}
        except (
            RuntimeError,
            OSError,
            AttributeError,
            LookupError,
            yaml.YAMLError,
        ) as exc:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.FAIL,
                message=f"Failed to read application.yaml: {exc}",
            )

        missing: list[str] = []
        present: list[str] = []

        for provider_key, pkg_name in _PROVIDER_PACKAGES.items():
            if provider_key not in config:
                continue
            try:
                distribution(pkg_name)
                present.append(provider_key)
            except PackageNotFoundError:
                missing.append(f"{provider_key} (needs {pkg_name})")

        if not (missing or present):
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.SKIP,
                message="No known provider sections in application.yaml",
            )
        if missing:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.FAIL,
                message=f"Missing packages for: {', '.join(missing)}",
                details={"missing": missing, "present": present},
            )
        return CheckResult(
            name=self.get_name(),
            status=CheckStatus.PASS,
            message=f"All {len(present)} configured provider package(s) installed",
        )


class CrossExtensionImportCheck(HealthCheck):
    """Detect direct cross-extension imports that violate the dependency graph.

    Scans every ``*.py`` file under ``src/`` using Python's ``ast`` module
    and flags any ``import`` or ``from … import`` that crosses the boundary
    between two lexigram extension namespaces (e.g. ``lexigram.web`` importing
    from ``lexigram.sql`` directly instead of through contracts).
    """

    #: (source prefix, forbidden_import_prefix) pairs.
    _FORBIDDEN_PAIRS: list[tuple[str, str]] = [
        ("lexigram.web", "lexigram.sql"),
        ("lexigram.web", "lexigram.cache"),
        ("lexigram.web", "lexigram.tasks"),
        ("lexigram.auth", "lexigram.sql"),
        ("lexigram.auth", "lexigram.cache"),
        ("lexigram.cache", "lexigram.sql"),
        ("lexigram.tasks", "lexigram.sql"),
        ("lexigram.tasks", "lexigram.web"),
        ("lexigram.search", "lexigram.sql"),
        ("lexigram.search", "lexigram.cache"),
    ]

    def get_name(self) -> str:
        """Return the display name of this check."""
        return "Architecture Violations"

    def get_category(self) -> str:
        """Return the grouping category for this check."""
        return "Architecture"

    def check(self) -> CheckResult:
        """Walk src/ with ast to find forbidden cross-extension import statements."""
        import ast

        src_path = Path("src")
        if not src_path.exists():
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.SKIP,
                message="No src/ directory found — skipping architecture check",
            )

        violations: list[str] = []

        for py_file in sorted(src_path.rglob("*.py")):
            # Determine which namespace this file belongs to
            module_path = str(py_file).replace("/", ".")
            owning_prefix: str | None = None
            for src_prefix, _ in self._FORBIDDEN_PAIRS:
                if src_prefix in module_path:
                    owning_prefix = src_prefix
                    break
            if owning_prefix is None:
                continue

            try:
                tree = ast.parse(py_file.read_text(), filename=str(py_file))
            except SyntaxError:
                continue

            # Collect all imported module names in this file
            imported_modules: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.append(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_modules.append(node.module)

            # Detect forbidden pairs
            for _, forbidden_prefix in [
                pair for pair in self._FORBIDDEN_PAIRS if pair[0] == owning_prefix
            ]:
                if any(
                    m == forbidden_prefix or m.startswith(forbidden_prefix + ".")
                    for m in imported_modules
                ):
                    violations.append(
                        f"{py_file}: {owning_prefix} imports from {forbidden_prefix}"
                    )

        if violations:
            return CheckResult(
                name=self.get_name(),
                status=CheckStatus.FAIL,
                message=f"{len(violations)} cross-extension violation(s) found",
                details={"violations": violations},
            )
        return CheckResult(
            name=self.get_name(),
            status=CheckStatus.PASS,
            message="No cross-extension import violations detected",
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
