"""MCPController generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class MCPControllerGenerator(GeneratorBase):
    """Generates an MCPController class with @tool, @resource, and @prompt examples.

    Usage::

        lexigram gen mcp-controller DataTools

    This creates ``data_tools_controller.py`` in the output directory
    containing a fully-annotated ``DataToolsController(MCPController)`` class
    with example implementations for all three MCP primitives.
    """

    name = "mcp-controller"

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
        """Generate an MCPController file.

        Args:
            name: Controller name, e.g. ``"DataTools"`` or ``"user_service"``.
                  File name is derived from this.
            dry_run: When ``True``, compute output paths without writing.
            force: When ``True``, overwrite an existing file.

        Returns:
            ``GenerationResult`` with paths of created/skipped files.
        """
        result = GenerationResult()
        module_name = self._to_snake_case(name).removesuffix("_controller")
        class_name = self._to_pascal_case(module_name)
        # Strip trailing "Controller" from the class name if present
        if class_name.endswith("Controller"):
            class_name = class_name[: -len("Controller")]

        file_name = f"{module_name}_controller.py"
        file_path = self.output_dir / file_name

        if file_path.exists() and not force:
            result.files_skipped.append(file_path)
            return result

        # Build a URI-friendly resource name (simple pluralisation)
        resource_name = module_name.replace("_", " ")
        if not resource_name.endswith("s"):
            resource_name += "s"

        context: dict[str, Any] = {
            "class_name": class_name,
            "module_name": module_name,
            "tool_prefix": module_name,
            "resource_name": resource_name,
            "resource_uri": f"{module_name}://",
        }

        template = self.env.get_template("mcp_controller.py.jinja2")
        content = template.render(**context)

        if not dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            result.files_created.append(file_path)
        else:
            result.files_created.append(file_path)

        return result
