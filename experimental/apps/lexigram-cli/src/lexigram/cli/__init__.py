"""Lexigram CLI - Command-line tools for Lexigram Framework."""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.cli.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.cli.config import CLIConfig
    from lexigram.cli.exceptions import (
        CliError,
        ConfigNotFoundError,
        ProviderNotInstalledError,
    )
    from lexigram.cli.lib import (
        find_config,
        load_config_yaml,
    )
    from lexigram.cli.output import OutputManager
    from lexigram.cli.protocols import (
        CLIApplicationProtocol,
        CLIRunnerProtocol,
        CommandProtocol,
    )
    from lexigram.cli.runtime import (
        CLIContext,
        handle_errors,
    )

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "CLIApplicationProtocol": ("lexigram.cli.protocols", "CLIApplicationProtocol"),
    "CLIConfig": ("lexigram.cli.config", "CLIConfig"),
    "CLIContext": ("lexigram.cli.runtime", "CLIContext"),
    "CLIModule": ("lexigram.cli.module", "CLIModule"),
    "CLIRunnerProtocol": ("lexigram.cli.protocols", "CLIRunnerProtocol"),
    "CliError": ("lexigram.cli.exceptions", "CliError"),
    "CommandProtocol": ("lexigram.cli.protocols", "CommandProtocol"),
    "ConfigNotFoundError": ("lexigram.cli.exceptions", "ConfigNotFoundError"),
    "ProviderNotInstalledError": (
        "lexigram.cli.exceptions",
        "ProviderNotInstalledError",
    ),
    "OutputManager": ("lexigram.cli.output", "OutputManager"),
    "handle_errors": ("lexigram.cli.runtime", "handle_errors"),
    "find_config": ("lexigram.cli.lib", "find_config"),
    "load_config_yaml": ("lexigram.cli.lib", "load_config_yaml"),
}


def __getattr__(name: str) -> Any:
    """Lazy load attributes to avoid circular imports."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes for IDE support."""
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "CLIApplicationProtocol",
    "CLIConfig",
    "CLIContext",
    "CLIModule",
    "CLIRunnerProtocol",
    "CliError",
    "CommandProtocol",
    "ConfigNotFoundError",
    "OutputManager",
    "ProviderNotInstalledError",
    "find_config",
    "handle_errors",
    "load_config_yaml",
]
