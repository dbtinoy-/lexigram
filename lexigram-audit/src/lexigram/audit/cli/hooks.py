"""CLI lifecycle hooks for lexigram-audit."""

from __future__ import annotations


def log_cli_command(ctx: object) -> None:
    """Write an audit log entry for every CLI command executed.

    Args:
        ctx: CLI context with command name and arguments.
    """
