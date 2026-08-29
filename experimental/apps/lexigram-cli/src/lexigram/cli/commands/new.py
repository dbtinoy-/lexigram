"""lexigram new — scaffold projects and extension packages."""

from __future__ import annotations

from pathlib import Path
import re

import typer

from lexigram.cli.layout import STRUCTURES
from lexigram.cli.output import OutputManager
from lexigram.cli.scaffold import (
    render_module,
    render_project,
    resolve_template,
    structure_names,
    template_names,
)

app = typer.Typer(name="new")


def _valid_name(value: str, kind: str) -> str:
    """Validate a project/package name is a safe Python module slug."""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
        raise typer.BadParameter(
            f"{kind} name must start with a letter and contain only "
            "letters, digits, dashes, or underscores."
        )
    return value


@app.command("project")
def main(
    name: str = typer.Argument(..., help="Name of the project"),
    template: str = typer.Option(
        "web-api",
        "--template",
        "-t",
        help="Project template",
    ),
    structure: str = typer.Option(
        "structured",
        "--structure",
        "-s",
        help="Project structure (minimal, structured, modular)",
    ),
    directory: str = typer.Option(".", "--directory", "-d", help="Target directory"),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Run interactive mode",
    ),
) -> None:
    """Create a new Lexigram project, fully aligned with the framework."""
    out = OutputManager()
    project_name = _valid_name(name, "Project")
    selected_template = template

    if interactive:
        selected_template = typer.prompt(
            "Select a template",
            default="web-api",
            type=typer.Choice(template_names()),
        )

    if structure not in STRUCTURES:
        out.error(
            f"Structure {structure} not found. "
            f"Available: {', '.join(structure_names())}."
        )
        raise typer.Exit(1)

    try:
        resolve_template(selected_template)
    except ValueError:
        out.error(f"Template {selected_template} not found")
        raise typer.Exit(1)

    target_dir = Path(directory) / project_name
    if target_dir.exists() and any(target_dir.iterdir()):
        out.error(f"Directory {target_dir} is not empty.")
        raise typer.Exit(1)

    out.print(
        f"[info]Creating project[/info] [bold]{project_name}[/bold] using "
        f"template [bold]{selected_template}[/bold]...",
    )

    created = render_project(
        selected_template,
        project_name,
        target_dir,
        structure=structure,
    )

    out.success(f"Project {project_name} created successfully!")
    out.print(
        f"[info]Scaffolded[/info] {len(created)} files "
        f"([bold]{selected_template}[/bold] template, "
        f"[bold]{structure}[/bold] structure).",
    )
    out.print(
        f"\n[bold]Next steps:[/bold]\n"
        f"  cd {project_name}\n"
        f"  pip install -e .\n"
        f"  lexigram gen list\n"
        f"  lexigram dev\n"
        f"  lexigram test",
    )


def _to_class_name(slug: str) -> str:
    """Convert a package slug like 'my-feature' to a PascalCase class name."""
    return "".join(part.capitalize() for part in re.split(r"[-_]", slug))


@app.command("module")
def module(
    name: str = typer.Argument(
        ..., help="Feature name (e.g. 'auth' -> modules/auth/AuthModule)"
    ),
    directory: str = typer.Option(
        ".",
        "--directory",
        "-d",
        help="Project root directory",
    ),
) -> None:
    """Create a bounded context inside a modular project."""
    out = OutputManager()
    module_name = _valid_name(name, "Module")
    try:
        created = render_module(module_name, Path(directory))
    except ValueError as exc:
        out.error(str(exc))
        raise typer.Exit(1)

    class_name = _to_class_name(module_name) + "Module"
    out.success(f"Module {class_name} created successfully! ({len(created)} files)")
    out.print(
        f"\n[bold]Next steps:[/bold]\n"
        f"  lexigram gen controller users --module {module_name}\n"
        f"  lexigram gen service billing --module {module_name}\n"
        f"  lexigram dev",
    )


@app.command("package")
def package(
    name: str = typer.Argument(
        ..., help="Package name (e.g. 'my-feature' → lexigram-my-feature)"
    ),
    description: str = typer.Option(
        "",
        "--description",
        "-d",
        help="Short description for the package",
    ),
    directory: str = typer.Option(".", "--directory", help="Target parent directory"),
) -> None:
    """Scaffold a new lexigram-* extension package.

    Creates lexigram-<name>/ with pyproject.toml, src/ layout, py.typed,
    di/provider.py, and a unit test scaffold.
    """
    out = OutputManager()

    # Normalise: strip leading "lexigram-" if user typed it
    slug = _valid_name(name.removeprefix("lexigram-"), "Package")
    package_name = slug.replace("-", "_")
    full_name = f"lexigram-{slug}"
    class_name = _to_class_name(slug)
    pkg_description = description or f"Lexigram extension package: {full_name}"

    target_dir = Path(directory) / full_name
    if target_dir.exists() and any(target_dir.iterdir()):
        out.error(f"Directory {target_dir} is not empty.")
        raise typer.Exit(1)

    out.print(f"[info]Scaffolding[/info] [bold]{full_name}[/bold]...")

    from lexigram.cli.scaffold_package import render_package

    created = render_package(
        package_name,
        target_dir,
        class_name=class_name,
        description=pkg_description,
    )

    out.success(f"{full_name} scaffolded successfully! ({len(created)} files)")
    out.print(
        f"\n[bold]Next steps:[/bold]\n  cd {full_name}\n  pip install -e .\n  pytest",
    )


__all__ = ["app"]
