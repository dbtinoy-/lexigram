"""CommandAssembler: wires CliContributorRegistry generators onto a Typer app."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from lexigram.cli.contributors.registry import CliContributorRegistry
from lexigram.cli.output import OutputManager
from lexigram.cli.registry.generator import GeneratorRegistry
from lexigram.cli.runtime import handle_errors
from lexigram.contracts.cli.types import GeneratorDefinition


def _detect_src_dir(default: str) -> str:
    """Rewrite package-local ``src`` defaults for single-package layouts."""
    default_path = Path(default)
    if not default_path.parts or default_path.parts[0] != "src":
        return default

    src_dir = Path.cwd() / "src"
    if not src_dir.is_dir():
        return default

    packages = [
        package_dir
        for package_dir in src_dir.iterdir()
        if package_dir.is_dir() and (package_dir / "__init__.py").is_file()
    ]
    if len(packages) != 1:
        return default

    package_relative_parts = ["src", packages[0].name, *default_path.parts[1:]]
    return str(Path(*package_relative_parts))


class CommandAssembler:
    """Wires generator definitions from all CLI contributors onto a Typer app."""

    def __init__(
        self,
        contributor_registry: CliContributorRegistry,
        generator_registry: GeneratorRegistry,
    ) -> None:
        self._contributor_registry = contributor_registry
        self._generator_registry = generator_registry

    def assemble(self, app: typer.Typer) -> None:
        """Register a Typer subcommand for every generator from all contributors."""
        for contributor in self._contributor_registry.get_all():
            for generator_definition in contributor.get_generators():
                self._register_command(app, generator_definition)

    def _register_command(
        self,
        app: typer.Typer,
        gen_def: GeneratorDefinition,
    ) -> None:
        """Register a single executable Typer subcommand for *gen_def*."""
        generator_name = gen_def.name
        registry = self._generator_registry

        @handle_errors
        def _command(
            name: str,
            fields: Annotated[
                str | None,
                typer.Option("--fields", "-f", help="Fields in name:type format"),
            ] = None,
            output_dir: Annotated[
                str,
                typer.Option("--output-dir", "-o", help="Output directory"),
            ] = gen_def.default_output_dir,
            dry_run: Annotated[
                bool,
                typer.Option(
                    "--dry-run",
                    help="Show what would be generated without writing to disk",
                ),
            ] = False,
            force: Annotated[
                bool,
                typer.Option("--force", help="Overwrite existing files"),
            ] = False,
        ) -> None:
            definition = registry.get(generator_name)
            if definition is None:
                typer.echo(
                    f"Generator {generator_name} is not registered in the generator registry.",
                    err=True,
                )
                raise typer.Exit(1)

            adapter = registry.get_adapter(generator_name)
            if adapter is None:
                typer.echo(
                    f"Generator {generator_name} is not registered in the generator registry.",
                    err=True,
                )
                raise typer.Exit(1)

            kwargs: dict[str, object] = {"dry_run": dry_run, "force": force}
            if fields:
                kwargs["fields_str"] = fields

            resolved_output = output_dir
            if output_dir == definition.default_output_dir:
                resolved_output = _detect_src_dir(output_dir)

            result = adapter.generate(name, output_dir=resolved_output, **kwargs)
            output = OutputManager()
            if result.success:
                for file_path in result.files_created:
                    output.success(f"Created: {file_path}")
                for file_path in result.files_updated:
                    output.warning(f"Overwrote: {file_path}")
                if not result.files_created and not result.files_updated:
                    output.info("No files generated")
                return

            output.error(f"Generation failed: {result.error}")
            raise typer.Exit(1)

        _command.__name__ = generator_name.replace("-", "_")
        app.command(generator_name, help=gen_def.description)(_command)


__all__ = ["CommandAssembler"]
