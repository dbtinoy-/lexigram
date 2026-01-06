"""Version registry for version management.

This module provides a registry pattern for version information.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
import subprocess

from lexigram.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VersionInfo:
    """Information about a package version."""

    name: str
    version: str
    installed: bool = True


class VersionSource(abc.ABC):
    """Abstract base class for version sources."""

    name: str

    @abc.abstractmethod
    def get_version(self) -> str | None:
        """Get the version of a package."""


class PyPackageVersionSource(VersionSource):
    """Get version from installed Python package."""

    def __init__(self, package_name: str):
        self.package_name = package_name

    def get_version(self) -> str | None:
        try:
            import importlib.metadata

            return importlib.metadata.version(self.package_name)
        except (RuntimeError, OSError, AttributeError, LookupError):
            return None


class GitVersionSource(VersionSource):
    """Get version from git tags."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def get_version(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                check=False,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (RuntimeError, OSError, AttributeError, LookupError) as exc:
            logger.debug("version_check_failed", error=str(exc))
        return None


class VersionRegistry:
    """Registry for version information.

    Provides a pluggable way to get versions of packages.
    """

    _sources: dict[str, VersionSource] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, name: str, source: VersionSource) -> None:
        """Register a version source."""
        cls._sources[name] = source

    @classmethod
    def get(cls, name: str) -> VersionSource | None:
        """Get a version source by name."""
        return cls._sources.get(name)

    @classmethod
    def get_all(cls) -> dict[str, VersionSource]:
        """Get all registered sources."""
        return cls._sources.copy()

    @classmethod
    def register_defaults(cls) -> None:
        """Initialize default sources if not already done."""
        if not cls._initialized:
            cls.register("lexigram", PyPackageVersionSource("lexigram"))
            cls.register("python", PyPackageVersionSource("python"))
            cls.register("uv", PyPackageVersionSource("uv"))
            cls.register("pytest", PyPackageVersionSource("pytest"))
            cls.register("ruff", PyPackageVersionSource("ruff"))
            cls.register("mypy", PyPackageVersionSource("mypy"))
            cls._initialized = True


def get_version(package: str) -> str | None:
    """Get version of a package."""
    VersionRegistry.register_defaults()
    source = VersionRegistry.get(package.lower())
    if source:
        return source.get_version()
    return PyPackageVersionSource(package).get_version()


def get_all_versions() -> dict[str, str]:
    """Get versions of all registered packages."""
    VersionRegistry.register_defaults()
    versions = {}
    for name, source in VersionRegistry.get_all().items():
        version = source.get_version()
        if version:
            versions[name] = version
    return versions


__all__ = [
    "GitVersionSource",
    "PyPackageVersionSource",
    "VersionInfo",
    "VersionRegistry",
    "VersionSource",
    "get_all_versions",
    "get_version",
]
