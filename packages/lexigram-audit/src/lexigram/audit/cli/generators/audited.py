"""Audited handler generator for the audit package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import GenerationResult, GeneratorBase
from lexigram.contracts.cli.generators import resolve_options


class AuditedHandlerGenerator(GeneratorBase):
    """Generate an async handler wrapped with the audit decorator."""

    name = "audited"
    description = "Generate an audited async handler"
    default_output_dir = "src/audit"

    def __init__(self, output_dir: str | Path = "src/audit") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        action: str | None = None,
        resource_type: str | None = None,
        severity: str = "medium",
        doc: str | None = None,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate an audited handler module.

        Args:
            name: Handler name (e.g. ``"UpdateUser"`` or ``"update_user"``).
            action: Dot-notation action identifier; derived from *name* when
                omitted (e.g. ``"update_user.execute"``).
            resource_type: Kind of affected resource (e.g. ``"User"``).
            severity: Default severity level for the audit entry.
            doc: Optional module docstring note.
            dry_run: Compute output paths without writing.
            force: Overwrite an existing file.

        Returns:
            ``GenerationResult`` with created/skipped/overwritten paths.
        """
        snake_name = self._to_snake_case(name)
        class_name = self._to_pascal_case(name)
        content = self.render_template(
            "audited.py.jinja2",
            {
                "class_name": class_name,
                "action": action or f"{snake_name}.execute",
                "resource_type": resource_type or class_name,
                "severity": severity,
                "doc": doc,
            },
        )
        file_path = self.output_dir / f"{snake_name}_audited.py"
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))


__all__ = ["AuditedHandlerGenerator"]
