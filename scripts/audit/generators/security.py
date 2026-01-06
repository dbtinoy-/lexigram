from __future__ import annotations

from pathlib import Path

from scripts.audit.generators.base import MarkdownAuditGenerator

_SECURITY_TARGETS = {
    "lexigram-contracts/src/lexigram/contracts/security": "Contracts Security",
    "lexigram/src/lexigram/security": "Core Security",
    "lexigram/src/lexigram/auth": "Authentication",
}


class SecurityAuditGenerator(MarkdownAuditGenerator):
    """Generate a lightweight security audit."""

    name = "security"
    description = "Generate AUDIT_SECURITY.md from security-related module paths."
    output_file = "AUDIT_SECURITY.md"

    def render_markdown(self, *, root: Path) -> str:
        """Render security markdown."""

        markdown = """# AUDIT_SECURITY.md — Lexigram Framework Security Inventory

> **Source**: Security-related framework module paths.

---

## Security Modules

"""
        markdown += "| Area | Path | Public Modules |\n"
        markdown += "|------|------|----------------|\n"
        for relative_path, label in _SECURITY_TARGETS.items():
            module_path = root / relative_path
            modules = ", ".join(_find_public_modules(module_path)) or "-"
            markdown += f"| {label} | `{relative_path}` | {modules} |\n"
        markdown += "\n"
        return markdown


def _find_public_modules(module_path: Path) -> tuple[str, ...]:
    """Find public Python module names under a directory."""

    if not module_path.is_dir():
        return ()
    return tuple(
        sorted(
            file_path.stem
            for file_path in module_path.rglob("*.py")
            if not file_path.name.startswith("_")
        )
    )
