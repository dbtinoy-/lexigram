"""Add provider command using registry pattern."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml

from lexigram.cli.output import OutputManager
from lexigram.cli.registry.provider import ProviderInstaller, ProviderRegistry

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(
    provider: str = typer.Argument(..., help="Provider to add (e.g., database, auth)"),
):
    """Add a provider to the project."""
    out = OutputManager()

    provider_obj = ProviderRegistry().get(provider)
    if not provider_obj:
        out.error(f"Unknown provider: {provider}")
        out.info(f"Available providers: {', '.join(ProviderRegistry().get_choices())}")
        raise typer.Exit(1)

    info = provider_obj.get_info()

    out.print(
        f"[info]Adding provider[/info] [bold]{provider}[/bold] ([dim]{info.package}[/dim])...",
    )

    pyproject_path = Path("pyproject.toml")
    if pyproject_path.exists():
        out.info("Updating pyproject.toml...")
        installed = ProviderInstaller.install_provider(provider_obj)
        if installed:
            out.success(f"Added {info.package} to dependencies")
        else:
            out.warning(f"Could not install {info.package} automatically")
            out.info(f"Run 'uv add {info.package}' to install manually")
    else:
        out.warning("pyproject.toml not found, skipping dependency update.")

    config_path = Path("application.yaml")
    if config_path.exists():
        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}

            for key, value in info.config.items():
                if key not in config_data:
                    config_data[key] = value
                    out.success(f"Added {key} section to application.yaml")
                else:
                    out.info(
                        f"{key} section already exists in application.yaml, skipping.",
                    )

            with open(config_path, "w") as f:
                yaml.dump(config_data, f, sort_keys=False)

        except (OSError, yaml.YAMLError, ValueError) as e:
            out.error(f"Failed to update application.yaml: {e}")
    else:
        out.warning("application.yaml not found, skipping config update.")

    out.success(f"Provider {provider} added successfully!")


__all__ = ["app"]
