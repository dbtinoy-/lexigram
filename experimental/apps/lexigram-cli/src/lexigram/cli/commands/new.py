from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
from typing import Any

from jinja2 import Environment, FileSystemLoader
import typer

from lexigram.cli.output import OutputManager

app = typer.Typer(name="new")

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "project"
PACKAGE_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "package"


def render_template(template_path: Path, output_path: Path, context: dict[str, Any]) -> None:
    env = Environment(loader=FileSystemLoader(str(template_path)))  # noqa: S701 — CLI scaffold templates, no HTML context

    for root, _dirs, files in os.walk(template_path):
        rel_path = Path(root).relative_to(template_path)
        rel_path_str = str(rel_path).replace(
            "{{ package_name }}",
            context.get("package_name", ""),
        )
        target_dir = output_path / rel_path_str

        if not target_dir.exists():
            target_dir.mkdir(parents=True)

        for file in files:
            file_path = Path(root) / file
            target_file = target_dir / file.replace(
                "{{ package_name }}",
                context.get("package_name", ""),
            )

            if file.endswith(".pyc") or "__pycache__" in str(file_path):
                continue

            try:
                template = env.get_template(str(rel_path / file))
                content = template.render(**context)

                with open(target_file, "w") as f:
                    f.write(content)
            except (OSError, ValueError, RuntimeError):
                shutil.copy2(file_path, target_file)


@app.command("project")
def main(
    name: str = typer.Argument(..., help="Name of the project"),
    template: str = typer.Option(
        "web-api",
        "--template",
        "-t",
        help="Project template",
    ),
    directory: str = typer.Option(".", "--directory", "-d", help="Target directory"),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Run interactive mode",
    ),
) -> None:
    """
    Create a new Lexigram project.
    """
    out = OutputManager()
    project_name = name
    selected_template = template
    selected_database: str = "none"
    selected_auth: str = "none"

    if interactive:
        if not project_name:
            project_name = typer.prompt("Project Name")

        templates = [
            d.name for d in filter(lambda d: d.is_dir(), TEMPLATE_DIR.iterdir())
        ]
        selected_template = typer.prompt(
            "Select a template",
            default="web-api",
            type=typer.Choice(templates),  # type: ignore[attr-defined]
        )

        selected_database = typer.prompt(
            "Select a database",
            default="sqlite",
            type=typer.Choice(["sqlite", "postgres", "none"]),  # type: ignore[attr-defined]
        )

        selected_auth = typer.prompt(
            "Select authentication",
            default="none",
            type=typer.Choice(["none", "jwt"]),  # type: ignore[attr-defined]
        )

    if not project_name:
        out.error("Project name is required.")
        raise typer.Exit(1)

    target_dir = Path(directory) / project_name
    if target_dir.exists() and any(target_dir.iterdir()):
        out.error(f"Directory {target_dir} is not empty.")
        raise typer.Exit(1)

    template_path = TEMPLATE_DIR / selected_template
    if not template_path.exists():
        out.error(f"Template {selected_template} not found.")
        raise typer.Exit(1)

    out.print(
        f"[info]Creating project[/info] [bold]{project_name}[/bold] using template [bold]{selected_template}[/bold]...",
    )

    context = {
        "project_name": project_name,
        "package_name": project_name.replace("-", "_"),
        "database": selected_database,
        "auth": selected_auth,
    }

    render_template(template_path, target_dir, context)

    out.success(f"Project {project_name} created successfully!")
    out.print(
        f"\n[bold]Next steps:[/bold]\n  cd {project_name}\n  pip install -e .\n  lexigram dev",
    )


def _to_class_name(slug: str) -> str:
    """Convert a package slug like 'my-feature' to a PascalCase class name."""
    return "".join(part.capitalize() for part in re.split(r"[-_]", slug))


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
    slug = name.removeprefix("lexigram-")
    package_name = slug.replace("-", "_")
    full_name = f"lexigram-{slug}"
    class_name = _to_class_name(slug)
    pkg_description = description or f"Lexigram extension package: {full_name}"

    target_dir = Path(directory) / full_name
    if target_dir.exists() and any(target_dir.iterdir()):
        out.error(f"Directory {target_dir} is not empty.")
        raise typer.Exit(1)

    if not PACKAGE_TEMPLATE_DIR.exists():
        out.error(f"Package template not found at {PACKAGE_TEMPLATE_DIR}.")
        raise typer.Exit(1)

    out.print(
        f"[info]Scaffolding[/info] [bold]{full_name}[/bold]...",
    )

    context: dict[str, Any] = {
        "package_name": package_name,
        "class_name": class_name,
        "description": pkg_description,
    }

    render_template(PACKAGE_TEMPLATE_DIR, target_dir, context)

    out.success(f"{full_name} scaffolded successfully!")
    out.print(
        f"\n[bold]Next steps:[/bold]\n  cd {full_name}\n  uv sync\n  uv run pytest",
    )


__all__ = ["app"]
