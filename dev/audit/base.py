"""Base audit generator classes for AUDIT file automation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class AuditOptions:
    """Options for running audit generators."""

    verbose: bool = False
    dry_run: bool = False
    output_dir: Path = Path()
    parallel: bool = True
    max_workers: int = 4
    force: bool = False
    generators: list[str] | None = None


@dataclass
class AuditResult:
    """Result of running an audit generator."""

    generator_name: str
    output_file: str
    success: bool
    message: str = ""
    lines_generated: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BaseAuditGenerator(ABC):
    """Base class for all AUDIT file generators.

    Each generator should inherit from this class and implement
    the `generate` method.
    """

    name: str = "base"
    output_file: str = "AUDIT_BASE.md"

    def __init__(self, options: AuditOptions | None = None):
        self.options = options or AuditOptions()
        self._results: list[AuditResult] = []

    @abstractmethod
    def generate(self) -> AuditResult:
        """Generate the audit content.

        Returns:
            AuditResult with the generated content information.
        """
        ...

    def validate(self) -> bool:
        """Validate that the generator can run.

        Returns:
            True if prerequisites are met.
        """
        return True

    def run(self) -> AuditResult:
        """Run the generator with validation.

        Returns:
            AuditResult from the generation.
        """
        if not self.validate():
            return AuditResult(
                generator_name=self.name,
                output_file=self.output_file,
                success=False,
                message="Validation failed",
            )

        return self.generate()

    def _get_workspace_root(self) -> Path:
        """Get the workspace root directory.

        Returns:
            Path to the workspace root.
        """
        # Start from this script's location and navigate up
        current = Path(__file__).resolve()
        # Go up from scripts/audit/base.py to workspace root
        # /path/to/lexigram/scripts/audit/base.py -> /path/to/lexigram/
        return current.parent.parent.parent

    def _read_template(self, template_name: str) -> str:
        """Get the header template for AUDIT files.

        Args:
            template_name: Name to include in the template.

        Returns:
            Formatted template string.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""# AUDIT_{template_name.upper()}.md — Lexigram Framework {self._get_title()}

> **Generated**: {timestamp}
> **Generator**: {self.name}.py
> **Source**: {self._get_source()}

---

"""

    def _get_title(self) -> str:
        """Get the title/description for this audit type.

        Override in subclasses.
        """
        return "Audit"

    def _get_source(self) -> str:
        """Get the source description for this audit type.

        Override in subclasses.
        """
        return "Generated data"


class FileAuditGenerator(BaseAuditGenerator):
    """Generator that writes output to a file."""

    def generate(self) -> AuditResult:
        """Generate content and write to file.

        Returns:
            AuditResult with file write information.
        """
        content = self._generate_content()

        output_path = self.options.output_dir / self.output_file

        if self.options.dry_run:
            return AuditResult(
                generator_name=self.name,
                output_file=str(output_path),
                success=True,
                message=f"DRY RUN - Would write {len(content)} characters",
                lines_generated=len(content.splitlines()),
            )

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        output_path.write_text(content, encoding="utf-8")

        return AuditResult(
            generator_name=self.name,
            output_file=str(output_path),
            success=True,
            message=f"Written to {output_path}",
            lines_generated=len(content.splitlines()),
        )

    @abstractmethod
    def _generate_content(self) -> str:
        """Generate the actual content.

        Returns:
            Generated content as string.
        """
        ...


class TestableAuditGenerator(FileAuditGenerator):
    """Generator that runs pytest to collect test information."""

    name: str = "tests"
    output_file: str = "AUDIT_TESTS.md"

    def _get_title(self) -> str:
        return "Test Summary"

    def _get_source(self) -> str:
        return "pytest test runs"

    def validate(self) -> bool:
        """Check that pytest is available."""
        workspace = self._get_workspace_root()
        return (workspace / "pyproject.toml").exists()

    def _generate_content(self) -> str:
        """Generate test summary content."""
        workspace = self._get_workspace_root()
        content = self._read_template(self.name)

        # Add basic summary
        content += "## Test Summary\n\n"
        content += "| Package | Status |\n"
        content += "|--------|--------|\n"
        content += f"| lexigram | {self._run_tests(workspace, 'lexigram')} |\n\n"

        return content

    def _run_tests(self, workspace: Path, package: str) -> str:
        """Run tests for a package.

        Args:
            workspace: Workspace root path.
            package: Package to test.

        Returns:
            Status string.
        """
        # Simplified - just return placeholder
        # Full implementation would use subprocess
        return "See full report"
