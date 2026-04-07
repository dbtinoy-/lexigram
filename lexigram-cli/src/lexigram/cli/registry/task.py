"""Task runner registry for project commands.

This module provides a registry pattern for task runners (test, lint, etc).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
import shutil
import subprocess
from typing import Any, ClassVar


@dataclass
class TaskResult:
    """Result of a task execution."""

    success: bool
    message: str = ""
    output: str = ""
    exit_code: int = 0


class TaskRunner(abc.ABC):
    """Abstract base class for task runners."""

    name: ClassVar[str]
    description: ClassVar[str]

    @abc.abstractmethod
    def get_name(self) -> str:
        """Get the name of this task runner."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check if the required tools are available."""

    @abc.abstractmethod
    def run(self, **options: Any) -> TaskResult:
        """Run the task."""


class PytestRunner(TaskRunner):
    """Pytest test runner."""

    name = "pytest"
    description = "Run project tests"

    def get_name(self) -> str:
        return self.name

    def is_available(self) -> bool:
        return shutil.which("pytest") is not None

    def run(
        self,
        path: str = ".",
        coverage: bool = False,
        verbose: bool = False,
        **options: Any,
    ) -> TaskResult:
        cmd = ["pytest", path]
        if coverage:
            cmd.extend(["--cov=src", "--cov-report=term-missing"])
        if verbose:
            cmd.append("-v")

        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
            )
            return TaskResult(
                success=result.returncode == 0,
                output=result.stdout + result.stderr,
                exit_code=result.returncode,
            )
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            return TaskResult(
                success=False,
                message=f"Failed to run pytest: {e}",
            )


class RuffRunner(TaskRunner):
    """Ruff linter runner."""

    name = "ruff"
    description = "Run project linting"

    def get_name(self) -> str:
        return self.name

    def is_available(self) -> bool:
        return shutil.which("ruff") is not None

    def run(
        self,
        path: str = ".",
        fix: bool = False,
        **options: Any,
    ) -> TaskResult:
        cmd = ["ruff", "check", path]
        if fix:
            cmd.append("--fix")

        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
            )
            return TaskResult(
                success=result.returncode == 0,
                output=result.stdout + result.stderr,
                exit_code=result.returncode,
            )
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            return TaskResult(
                success=False,
                message=f"Failed to run ruff: {e}",
            )


class MypyRunner(TaskRunner):
    """Mypy type checker runner."""

    name = "mypy"
    description = "Run type checking"

    def get_name(self) -> str:
        return self.name

    def is_available(self) -> bool:
        return shutil.which("mypy") is not None

    def run(
        self,
        path: str = "src",
        **options: Any,
    ) -> TaskResult:
        cmd = ["mypy", path]

        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
            )
            return TaskResult(
                success=result.returncode == 0,
                output=result.stdout + result.stderr,
                exit_code=result.returncode,
            )
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            return TaskResult(
                success=False,
                message=f"Failed to run mypy: {e}",
            )


class TaskRunnerRegistry:
    """Registry for task runners.

    Provides a pluggable way to add new task runners.
    """

    _runners: dict[str, TaskRunner] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, runner: type[TaskRunner]) -> None:
        """Register a task runner class."""
        instance = runner()
        cls._runners[runner.name] = instance

    @classmethod
    def get(cls, name: str) -> TaskRunner | None:
        """Get a runner by name."""
        cls.register_defaults()
        return cls._runners.get(name)

    @classmethod
    def get_all(cls) -> dict[str, TaskRunner]:
        """Get all registered runners."""
        cls.register_defaults()
        return cls._runners.copy()

    @classmethod
    def get_available(cls) -> list[TaskRunner]:
        """Get all available (installed) runners."""
        cls.register_defaults()
        return [r for r in cls._runners.values() if r.is_available()]

    @classmethod
    def register_defaults(cls) -> None:
        """Initialize default runners if not already done."""
        if not cls._initialized:
            cls.register(PytestRunner)
            cls.register(RuffRunner)
            cls.register(MypyRunner)
            cls._initialized = True


__all__ = [
    "MypyRunner",
    "PytestRunner",
    "RuffRunner",
    "TaskResult",
    "TaskRunner",
    "TaskRunnerRegistry",
]
