"""Smart run command — auto-detects create_app() factory and launches ASGI server."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Annotated

import typer

from lexigram.cli.lib.entry_point import detect_factory_attr, path_to_module
from lexigram.cli.output import OutputManager
from lexigram.cli.registry.server import (
    ServerConfig,
    ServerManager,
    ServerRegistry,
    discover_entry_point,
)
from lexigram.cli.runtime import handle_errors

app = typer.Typer(name="run", invoke_without_command=True)


def _is_factory(attr: str) -> bool:
    """Return True when the attr is a callable factory (not a module-level app object)."""
    return attr == "create_app"


@app.callback(invoke_without_command=True)
@handle_errors
def main(
    target: Annotated[
        str | None,
        typer.Argument(
            help="Module:attr target, e.g. my_app.app:create_app. Auto-detected if omitted."
        ),
    ] = None,
    host: Annotated[
        str, typer.Option("--host", "-h", help="Host to bind")
    ] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Port to bind")] = 8000,
    reload: Annotated[
        bool, typer.Option("--reload/--no-reload", help="Hot reload")
    ] = True,
    workers: Annotated[
        int, typer.Option("--workers", "-w", help="Worker processes")
    ] = 1,
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="Config profile (sets LEX_PROFILE)"),
    ] = None,
    server: Annotated[
        str | None,
        typer.Option("--server", help="Server backend (uvicorn, hypercorn, granian)"),
    ] = None,
    mcp_port: Annotated[
        int | None,
        typer.Option(
            "--mcp-port",
            help=(
                "Also serve MCP (SSE) on this port alongside the web server. "
                "Requires MCPModule in your app's module list."
            ),
        ),
    ] = None,
) -> None:
    """Start the application, auto-detecting entry point and factory."""
    out = OutputManager()

    env: dict[str, str] = {}
    if profile:
        env["LEX_PROFILE"] = profile
        out.print(f"[info]Profile: [bold]{profile}[/bold]")

    # Resolve the module:attr target
    if target and ":" in target:
        # Explicit module:attr — use as-is
        entry_point = target
        factory = _is_factory(target.split(":")[-1])
    else:
        # Auto-detect entry point from project structure
        file_path = target if target else discover_entry_point()
        if not file_path or not Path(file_path).exists():
            out.error(
                "Could not find an application entry point.",
                hint="Specify it as 'my_app.app:create_app' or use --entry.",
            )
            raise typer.Exit(1)

        attr = detect_factory_attr(file_path)
        if not attr:
            out.error(
                f"No ASGI app or factory found in {file_path}.",
                hint="Define 'app', 'asgi_app', or 'create_app' at module level.",
            )
            raise typer.Exit(1)

        module = path_to_module(file_path)
        entry_point = f"{module}:{attr}"
        factory = _is_factory(attr)

        out.print(f"[info]Detected entry point: [bold]{entry_point}[/bold]")

    # Select server backend
    server_backend = None
    if server:
        server_backend = ServerRegistry.get(server)
        if not server_backend:
            available = ", ".join(b.name for b in ServerRegistry.get_available())
            out.error(f"Unknown server: {server}", hint=f"Available: {available}")
            raise typer.Exit(1)

    if not server_backend:
        # Prefer granian → uvicorn
        for preferred in ("granian", "uvicorn"):
            b = ServerRegistry.get(preferred)
            if b and b.is_available():
                server_backend = b
                break
        if not server_backend:
            server_backend = ServerRegistry.get_default()

    out.print(f"[info]Server: [bold]{server_backend.name}[/bold]  {host}:{port}")

    config = ServerConfig(
        entry_point=entry_point,
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        env=env,
        factory=factory,
    )

    # Dual-protocol: also spawn MCP SSE server as a background subprocess.
    mcp_proc: subprocess.Popen[bytes] | None = None
    if mcp_port is not None:
        lexigram_bin = sys.argv[0] if sys.argv[0] else "lexigram"
        mcp_cmd = [
            lexigram_bin,
            "mcp",
            "serve",
            "--transport",
            "sse",
            "--port",
            str(mcp_port),
        ]
        if profile:
            mcp_cmd += ["--profile", profile]
        mcp_cmd.append(entry_point)
        out.print(
            f"[info]MCP (SSE): [bold]{host}:{mcp_port}[/bold]  "
            f"→ POST http://{host}:{mcp_port}/mcp"
        )
        mcp_proc = subprocess.Popen(mcp_cmd)

    try:
        manager = ServerManager(server_backend)
        if reload:
            manager.start_dev(config)
        else:
            manager.start(config)
    finally:
        if mcp_proc is not None:
            mcp_proc.terminate()
            mcp_proc.wait(timeout=5)
