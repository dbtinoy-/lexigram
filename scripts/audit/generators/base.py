from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

PROPRIETARY_PKGS: frozenset[str] = frozenset({
    "lexigram-admin",
    "lexigram-ai-guard", "lexigram-ai-governance",
    "lexigram-ai-evaluation", "lexigram-ai-prompt",
})


@dataclass(frozen=True, slots=True)
class AuditRunResult:
    """Structured result returned by an audit generator."""

    name: str
    success: bool
    message: str
    output_path: Path | None = None


@runtime_checkable
class AuditGeneratorProtocol(Protocol):
    """Contract for audit generators exposed by the scripts platform."""

    name: str
    description: str
    output_file: str
    env_vars: tuple[str, ...]

    def validate(self, *, root: Path | None = None) -> AuditRunResult:
        """Validate that the generator can run for the given workspace root."""

    def run(self, *, root: Path | None = None, all_mode: bool = False) -> AuditRunResult:
        """Execute the generator and return a structured result."""


class MarkdownAuditGenerator:
    """Shared base class for simple markdown-emitting audit generators."""

    name = ""
    description = ""
    output_file = ""
    env_vars: tuple[str, ...] = ()

    def resolve_root(self, root: Path | None = None) -> Path:
        """Resolve the workspace root for generator execution."""

        if root is not None:
            return root.resolve()
        return Path(__file__).resolve().parents[3]

    def validate(self, *, root: Path | None = None) -> AuditRunResult:
        """Validate that the workspace root exists and is a directory."""

        resolved_root = self.resolve_root(root)
        if not resolved_root.exists():
            return AuditRunResult(
                name=self.name,
                success=False,
                message=f"workspace root does not exist: {resolved_root}",
            )
        if not resolved_root.is_dir():
            return AuditRunResult(
                name=self.name,
                success=False,
                message=f"workspace root is not a directory: {resolved_root}",
            )
        return AuditRunResult(
            name=self.name,
            success=True,
            message=f"ready for {resolved_root}",
        )

    def run(self, *, root: Path | None = None, all_mode: bool = False) -> AuditRunResult:
        """Generate markdown and write it to the configured output file."""

        validation = self.validate(root=root)
        if not validation.success:
            return validation

        resolved_root = self.resolve_root(root)
        output_dir = resolved_root if all_mode else resolved_root / "docs/lexigram-docs/audit"
        output_dir.mkdir(parents=True, exist_ok=True)
        self._all_mode = all_mode
        try:
            markdown = self.render_markdown(root=resolved_root)
        finally:
            self._all_mode = False
        output_path = output_dir / self.output_file
        output_path.write_text(markdown, encoding="utf-8")
        return AuditRunResult(
            name=self.name,
            success=True,
            message=f"wrote {output_path.name}",
            output_path=output_path,
        )

    def render_markdown(self, *, root: Path) -> str:
        """Render markdown for the audit report."""

        raise NotImplementedError

    def iter_package_roots(self, *, root: Path) -> tuple[Path, ...]:
        """Return Lexigram package directories under the workspace root."""

        all_mode = getattr(self, "_all_mode", False)
        return tuple(
            sorted(
                path
                for path in root.iterdir()
                if path.is_dir()
                and (path.name == "lexigram" or path.name.startswith("lexigram-"))
                and (all_mode or path.name not in PROPRIETARY_PKGS)
            )
        )
