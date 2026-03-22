"""Gateway CLI helpers: config loading and runnable gateway assembly.

The orchestrator package discovers the relay, http, and web modules
through their entry-point groups (never direct imports), so the served
application is the same composition a user's own ``Application`` would
build: ``RelayModule`` + ``RelayGatewayModule`` (with the file-backed
configuration) + ``HTTPModule`` + ``WebModule``.
"""

from __future__ import annotations

from importlib import metadata
from pathlib import Path
from typing import Any

__all__ = ["build_gateway_app", "load_gateway_config", "serve_gateway"]


def load_gateway_config(path: str | Path) -> Any:
    """Load and validate a gateway configuration file (JSON or TOML).

    The file is parsed with the stdlib JSON/TOML parsers and validated
    through ``RelayGatewayConfig.from_mapping``.

    Args:
        path: Path to the configuration file.

    Returns:
        The validated ``RelayGatewayConfig``.

    Raises:
        ValueError: When the file is unreadable or the content is not a
            valid gateway configuration.
    """
    from lexigram.ai.relay.gateway.config import RelayGatewayConfig

    file_path = Path(path).expanduser()
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read gateway config file: {file_path}") from exc
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        from lexigram.serialization import loads

        try:
            data = loads(raw)
        except ValueError as exc:
            raise ValueError(f"invalid JSON in {file_path}: {exc}") from exc
    elif suffix in (".toml", ".tml"):
        import tomllib

        try:
            data = tomllib.loads(raw)
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"invalid TOML in {file_path}: {exc}") from exc
    else:
        raise ValueError("gateway config must be a .json or .toml file")
    if not isinstance(data, dict):
        raise TypeError("gateway config must be a JSON/TOML object")
    return RelayGatewayConfig.from_mapping(data)


def build_gateway_app(config: Any, host: str = "127.0.0.1") -> Any:
    """Assemble the runnable gateway ``Application`` for *config*.

    The relay, relay-gateway, http, and web modules are loaded from the
    ``lexigram.ai.modules`` and ``lexigram.modules`` entry-point groups;
    a missing module raises ``ModuleNotFoundError`` naming the group and
    entry.

    Args:
        config: The validated ``RelayGatewayConfig`` to serve.
        host: Bind host forwarded to ``WebModule.configure``.

    Returns:
        A composed, not-yet-started ``Application``.

    Raises:
        ModuleNotFoundError: When a required module entry point is not
            installed.
    """
    from lexigram.app.base import Application

    relay_module = _load_module("lexigram.ai.modules", "relay")
    gateway_module = _load_module("lexigram.ai.modules", "relay-gateway")
    http_module = _load_module("lexigram.modules", "http")
    web_module = _load_module("lexigram.modules", "web")

    app = Application(name="lexigram-relay-gateway")
    app.add_modules(
        [
            relay_module.configure(),
            gateway_module.configure(config=config),
            http_module.configure(),
            web_module.configure(host=host),
        ]
    )
    return app


def serve_gateway(
    config_path: str | Path, host: str = "127.0.0.1", port: int = 8000
) -> None:
    """Load the gateway config and serve the composed application.

    Args:
        config_path: Path to the gateway configuration file.
        host: Bind address.
        port: Bind port.
    """
    from lexigram.web.server.runner import run_server

    config = load_gateway_config(config_path)
    app = build_gateway_app(config, host=host)
    run_server(app, host=host, port=port)


def _load_module(group: str, name: str) -> Any:
    """Load one module class from *group* by entry-point *name*.

    Args:
        group: The entry-point group to inspect.
        name: The entry-point name to load.

    Returns:
        The loaded module class.

    Raises:
        ModuleNotFoundError: When the entry point is not registered.
    """
    matches = [ep for ep in metadata.entry_points(group=group) if ep.name == name]
    if not matches:
        raise ModuleNotFoundError(
            f"module entry point {name!r} not found in group {group!r}; "
            "is the package installed?"
        )
    return matches[0].load()
