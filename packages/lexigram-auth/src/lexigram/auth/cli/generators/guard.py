from __future__ import annotations

from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from lexigram.codegen.base import GenerationResult, GeneratorBase


class AuthGuardGenerator(GeneratorBase):
    name = "guard"
    description = "Generate an authorization guard"
    default_output_dir = "src/guards"

    def generate(
        self,
        name: str,
        **options: Any,
    ) -> GenerationResult:
        guard_type = options.get("type", "role")
        output_path = self.output_dir
        guard_name = self._to_pascal_case(name)
        guard_filename = f"{self._to_snake_case(name)}_guard.py"

        context = {
            "guard_name": guard_name,
            "guard_name_snake": self._to_snake_case(name),
            "package_name": self._get_package_name(self.output_dir),
            "guard_type": guard_type,
        }

        env = Environment(
            loader=PackageLoader("lexigram.auth.cli", "templates"),
            autoescape=select_autoescape(),
        )
        template = env.get_template("guard.py.jinja2")
        content = template.render(**context)

        file_path = output_path / guard_filename
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()

        if not options.get("dry_run", False):
            output_path.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
            return GenerationResult(files_created=[file_path])

        return GenerationResult()
