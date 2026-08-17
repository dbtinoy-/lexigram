"""``lexigram-ui add`` — copy components into the user's project."""

from __future__ import annotations

from pathlib import Path
import shutil

import typer

from lexigram.ui.cli.registry import COMPONENT_REGISTRY, ComponentEntry

app = typer.Typer(name="add")


@app.command()
def add(
    component_name: str = typer.Argument(
        ..., help="Component name (e.g. 'button', 'card')"
    ),
    output_dir: str = typer.Option(
        "src/components/ui", "--output", "-o", help="Output directory"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
) -> None:
    """Copy a UI component into your project."""
    entry = COMPONENT_REGISTRY.get(component_name)
    if entry is None:
        available = ", ".join(sorted(COMPONENT_REGISTRY))
        typer.echo(f"Unknown component: {component_name!r}", err=True)
        typer.echo(f"Available: {available}", err=True)
        raise typer.Exit(1)

    ui_pkg = _find_ui_package()
    if ui_pkg is None:
        typer.echo(
            "Cannot locate lexigram-ui source. Install it in editable mode:\n"
            "  uv pip install -e path/to/lexigram-ui",
            err=True,
        )
        raise typer.Exit(1)

    all_files = _collect_files(entry, ui_pkg)
    out_root = Path(output_dir)

    copied: list[Path] = []
    skipped: list[Path] = []

    for src in all_files:
        relative = src.relative_to(ui_pkg)
        dest = out_root / relative
        if dest.exists() and not force:
            skipped.append(dest)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(dest)

    if copied:
        typer.echo(f"Added {component_name} component:")
        for p in copied:
            typer.echo(f"  Created: {p}")
    if skipped:
        typer.echo("  Skipped (use --force to overwrite):")
        for p in skipped:
            typer.echo(f"  {p}")
    if not copied:
        typer.echo("No files were copied (all already exist).")


def _find_ui_package() -> Path | None:
    """Locate the lexigram-ui source directory (package root containing lexigram/)."""
    import lexigram.ui  # noqa: F811

    pkg_path = Path(lexigram.ui.__file__).resolve().parent
    # pkg_path is the ui module directory
    if pkg_path.name == "ui" and pkg_path.parent.name == "lexigram":
        # source layout: .../src/lexigram/ui/ or .../lexigram/ui/
        parent = pkg_path.parent.parent  # .../src/ or .../
        if (parent / "lexigram" / "ui").exists():
            return parent
        # Check if src/ prefix is present
        if parent.name == "src" and (parent.parent / "lexigram" / "ui").exists():
            return parent.parent
    return pkg_path.parent


def _collect_files(entry: ComponentEntry, ui_pkg: Path) -> list[Path]:
    """Collect all source files for a component and its dependencies."""
    seen: set[Path] = set()
    result: list[Path] = []

    def _add(dep_path: str) -> None:
        full = (ui_pkg / dep_path).resolve()
        if full.exists() and full not in seen:
            seen.add(full)
            result.append(full)
            for other in COMPONENT_REGISTRY.values():
                if dep_path.endswith(other.source_path):
                    for subdep in other.dependencies:
                        _add(subdep)

    _add(entry.source_path)
    for dep in entry.dependencies:
        _add(dep)

    return result


if __name__ == "__main__":
    app()
