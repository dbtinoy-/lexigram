"""AI CLI command group factory."""

from __future__ import annotations

import typer


def create_ai_app() -> typer.Typer:
    """Create the `lexigram ai` command group.

    Returns:
        A Typer app containing AI subsystem management subcommands.
    """
    app = typer.Typer(help="AI subsystem management commands")
    models_app = typer.Typer(help="Model management commands")
    providers_app = typer.Typer(help="Provider management commands")

    app.add_typer(models_app, name="models")
    app.add_typer(providers_app, name="providers")

    @app.command("status")
    def ai_status() -> None:
        """Show AI subsystem status."""
        typer.echo("AI subsystem status not yet implemented")

    @models_app.command("list")
    def list_models(
        provider: str | None = typer.Option(
            None, "--provider", help="Filter by provider name"
        ),
    ) -> None:
        """List available AI models."""
        typer.echo("AI model listing not yet implemented")

    @providers_app.command("list")
    def list_providers() -> None:
        """List registered AI providers."""
        typer.echo("AI provider listing not yet implemented")

    @app.command("config")
    def config_show() -> None:
        """Show current AI configuration."""
        typer.echo("AI configuration display not yet implemented")

    @app.command("test")
    def test_provider(
        provider: str = typer.Argument(..., help="Provider name to test"),
        prompt: str = typer.Option(
            "Hello, world!", "--prompt", help="Test prompt to send"
        ),
    ) -> None:
        """Test a specific AI provider with a prompt."""
        typer.echo(f"Testing provider {provider!r} not yet implemented")

    return app
