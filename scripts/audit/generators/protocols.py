from __future__ import annotations

from pathlib import Path
import re

from scripts.audit.generators.base import MarkdownAuditGenerator


class ProtocolsAuditGenerator(MarkdownAuditGenerator):
    """Generate a protocol inventory audit."""

    name = "protocols"
    description = "Generate AUDIT_PROTOCOLS.md from protocol class declarations."
    output_file = "AUDIT_PROTOCOLS.md"

    def render_markdown(self, *, root: Path) -> str:
        """Render protocol inventory markdown."""

        protocol_rows = list(_collect_protocol_rows(root))
        markdown = """# AUDIT_PROTOCOLS.md — Lexigram Framework Protocol Inventory

> **Source**: `class *Protocol` declarations across framework source trees.

---

## Summary

"""
        markdown += f"- Files with protocol declarations: {len(protocol_rows)}\n"
        markdown += (
            f"- Total protocol declarations: {sum(len(row['protocols']) for row in protocol_rows)}\n\n"
        )
        markdown += "## Protocol Files\n\n"
        markdown += "| File | Protocols |\n"
        markdown += "|------|-----------|\n"
        for row in protocol_rows:
            markdown += f"| `{row['path']}` | {', '.join(row['protocols'])} |\n"
        markdown += "\n"
        return markdown


def _collect_protocol_rows(root: Path) -> tuple[dict[str, str | list[str]], ...]:
    """Collect protocol declarations from selected source trees."""

    rows: list[dict[str, str | list[str]]] = []
    for source_root in (
        root / "lexigram-contracts" / "src",
        root / "lexigram" / "src",
    ):
        if not source_root.is_dir():
            continue
        for file_path in sorted(source_root.rglob("*.py")):
            content = file_path.read_text(encoding="utf-8")
            protocols = re.findall(r"^class\s+(\w+Protocol)\b", content, flags=re.MULTILINE)
            if protocols:
                rows.append(
                    {
                        "path": str(file_path.relative_to(root)),
                        "protocols": protocols,
                    }
                )
    return tuple(rows)
