from __future__ import annotations

from pathlib import Path

from scripts.audit.generators.base import AuditRunResult, MarkdownAuditGenerator
from scripts.audit.index import (
    build_audit_index,
    render_index_json,
    render_index_markdown,
)


class AuditIndexGenerator(MarkdownAuditGenerator):
    """Generate a bird's-eye audit index in markdown and JSON."""

    name = "index"
    description = "Generate AUDIT_INDEX.md and AUDIT_INDEX.json from registered audits."
    output_file = "AUDIT_INDEX.md"
    output_json_file = "AUDIT_INDEX.json"

    def run(self, *, root: Path | None = None, all_mode: bool = False) -> AuditRunResult:
        """Generate the audit index markdown and JSON outputs."""

        validation = self.validate(root=root)
        if not validation.success:
            return validation

        resolved_root = self.resolve_root(root)
        output_dir = resolved_root if all_mode else resolved_root / "docs/lexigram-docs/audit"
        output_dir.mkdir(parents=True, exist_ok=True)
        from scripts.audit.generators.registry import build_audit_registry

        snapshot = build_audit_index(
            resolved_root,
            build_audit_registry(),
            self_name=self.name,
            report_dir=output_dir,
        )
        markdown = render_index_markdown(
            snapshot,
            output_markdown=self.output_file,
            output_json=self.output_json_file,
        )
        json_text = render_index_json(
            snapshot,
            output_markdown=self.output_file,
            output_json=self.output_json_file,
        )

        markdown_path = output_dir / self.output_file
        json_path = output_dir / self.output_json_file
        markdown_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(json_text, encoding="utf-8")
        return AuditRunResult(
            name=self.name,
            success=True,
            message=f"wrote {markdown_path.name} and {json_path.name}",
            output_path=markdown_path,
        )
