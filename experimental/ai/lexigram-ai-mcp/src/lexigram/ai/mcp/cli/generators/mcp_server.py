"""MCP server script generator (Gear 1 — standalone script-mode)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class MCPServerGenerator(GeneratorBase):
    """Generates a standalone MCP server script with module-level decorators.

    Usage::

        lexigram gen mcp-server data_tools

    This creates ``data_tools_tools.py`` (script-mode Gear 1) with
    ``@tool``, ``@resource``, and ``@prompt`` decorated functions plus a
    ``__main__`` block so the file is directly executable::

        python data_tools_tools.py
        # — or —
        lexigram mcp serve data_tools_tools.py
    """

    name = "mcp-server"

    def __init__(self, output_dir: str = "src") -> None:
        super().__init__(
            output_dir=output_dir,
            template_root=Path(__file__).parent.parent / "templates",
        )

    def generate(
        self,
        name: str,
        dry_run: bool = False,
        force: bool = False,
        **_kwargs: Any,
    ) -> GenerationResult:
        """Generate a standalone MCP server script.

        Args:
            name: Base name for the server / module, e.g. ``"data_tools"``.
            dry_run: When ``True``, compute output paths without writing.
            force: When ``True``, overwrite an existing file.

        Returns:
            ``GenerationResult`` with paths of created/skipped files.
        """
        result = GenerationResult()
        module_name = self._to_snake_case(name).removesuffix("_tools")

        file_name = f"{module_name}_tools.py"
        file_path = self.output_dir / file_name

        if file_path.exists() and not force:
            result.files_skipped.append(file_path)
            return result

        resource_name = module_name.replace("_", " ")
        if not resource_name.endswith("s"):
            resource_name += "s"

        context: dict[str, Any] = {
            "module_name": module_name,
            "tool_prefix": module_name,
            "resource_name": resource_name,
            "resource_uri": f"{module_name}://",
        }

        template = self.env.get_template("mcp_server.py.jinja2")
        content = template.render(**context)

        if not dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            result.files_created.append(file_path)
        else:
            result.files_created.append(file_path)

        return result
