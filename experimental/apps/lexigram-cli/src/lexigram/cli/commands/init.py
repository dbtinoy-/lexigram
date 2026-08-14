"""lexigram init — initialize Lexigram in an existing project."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from lexigram.cli.output import OutputManager
from lexigram.cli.runtime import handle_errors

app = typer.Typer()

_MINIMAL_CONFIG = """\
project:
  name: {project_name}
  version: "0.1.0"

logging:
  level: INFO
"""

_FULL_CONFIG = """\
project:
  name: {project_name}
  version: "0.1.0"

logging:
  level: INFO
  format: json

web:
  host: "${{WEB_HOST:0.0.0.0}}"
  port: "${{WEB_PORT:8000}}"
  debug: false

database:
  url: "${{DATABASE_URL:sqlite:///./dev.db}}"
  echo: false

auth:
  enabled: false
  secret_key: "${{AUTH_SECRET_KEY}}"

cache:
  backend: memory

monitor:
  enabled: true
  health_path: /health
"""


@app.callback(invoke_without_command=True)
@handle_errors
def init(
    minimal: Annotated[
        bool,
        typer.Option("--minimal", help="Generate minimal config"),
    ] = False,
    full: Annotated[
        bool,
        typer.Option("--full", help="Generate config with all sections"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite existing config"),
    ] = False,
) -> None:
    """Initialize Lexigram in the current directory."""
    out = OutputManager()
    config_path = Path("application.yaml")

    if config_path.exists() and not force:
        out.error(
            f"{config_path} already exists",
            hint="Use --force to overwrite",
        )
        raise typer.Exit(1)

    project_name = Path.cwd().name
    template = _MINIMAL_CONFIG if minimal else _FULL_CONFIG if full else _MINIMAL_CONFIG
    content = template.format(project_name=project_name)
    config_path.write_text(content)
    out.success(f"Created {config_path}")


__all__ = ["app"]
