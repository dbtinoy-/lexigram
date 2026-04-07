"""Server backend registry for dev and start commands.

This module provides a registry pattern for supporting multiple ASGI server backends.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from typing import ClassVar


@dataclass
class ServerConfig:
    """Configuration for running a server."""

    entry_point: str
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    env: dict[str, str] = None  # type: ignore[assignment]
    factory: bool = False

    def __post_init__(self):
        if self.env is None:
            self.env = {}


class ServerBackend(abc.ABC):
    """Abstract base class for server backends."""

    name: ClassVar[str]
    package: ClassVar[str | None] = None

    @abc.abstractmethod
    def get_binary(self) -> str | None:
        """Get the path to the server binary."""

    @abc.abstractmethod
    def build_start_command(self, config: ServerConfig) -> list[str]:
        """Build the command to start the server."""

    @abc.abstractmethod
    def build_dev_command(self, config: ServerConfig) -> list[str]:
        """Build the command to start the server in development mode."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check if this server backend is available."""


class UvicornBackend(ServerBackend):
    """Uvicorn ASGI server."""

    name = "uvicorn"
    package = "uvicorn"

    def get_binary(self) -> str | None:
        return shutil.which("uvicorn")

    def build_start_command(self, config: ServerConfig) -> list[str]:
        cmd = [
            "uvicorn",
            config.entry_point,
            "--host",
            config.host,
            "--port",
            str(config.port),
        ]
        if config.workers > 1:
            cmd.extend(["--workers", str(config.workers)])
        if config.factory:
            cmd.append("--factory")
        return cmd

    def build_dev_command(self, config: ServerConfig) -> list[str]:
        cmd = [
            "uvicorn",
            config.entry_point,
            "--host",
            config.host,
            "--port",
            str(config.port),
            "--reload",
        ]
        if config.factory:
            cmd.append("--factory")
        return cmd

    def is_available(self) -> bool:
        return self.get_binary() is not None


class HypercornBackend(ServerBackend):
    """Hypercorn ASGI server."""

    name = "hypercorn"
    package = "hypercorn"

    def get_binary(self) -> str | None:
        return shutil.which("hypercorn")

    def build_start_command(self, config: ServerConfig) -> list[str]:
        cmd = [
            "hypercorn",
            config.entry_point,
            "--bind",
            f"{config.host}:{config.port}",
        ]
        if config.workers > 1:
            cmd.extend(["--workers", str(config.workers)])
        return cmd

    def build_dev_command(self, config: ServerConfig) -> list[str]:
        return [
            "hypercorn",
            config.entry_point,
            "--bind",
            f"{config.host}:{config.port}",
            "--reload",
        ]

    def is_available(self) -> bool:
        return self.get_binary() is not None


class GranianBackend(ServerBackend):
    """Granian ASGI server (Rust-based, high performance)."""

    name = "granian"
    package = "granian"

    def get_binary(self) -> str | None:
        return shutil.which("granian")

    def build_start_command(self, config: ServerConfig) -> list[str]:
        cmd = [
            "granian",
            "--interface",
            "asgi3",
            "--host",
            config.host,
            "--port",
            str(config.port),
            config.entry_point,
        ]
        if config.workers > 1:
            cmd.extend(["--workers", str(config.workers)])
        return cmd

    def build_dev_command(self, config: ServerConfig) -> list[str]:
        return [
            "granian",
            "--interface",
            "asgi3",
            "--host",
            config.host,
            "--port",
            str(config.port),
            "--reload",
            config.entry_point,
        ]

    def is_available(self) -> bool:
        return self.get_binary() is not None


class GunicornBackend(ServerBackend):
    """Gunicorn WSGI server (with gunicorn workers for ASGI)."""

    name = "gunicorn"
    package = "gunicorn"

    def get_binary(self) -> str | None:
        return shutil.which("gunicorn")

    def build_start_command(self, config: ServerConfig) -> list[str]:
        return [
            "gunicorn",
            "-w",
            str(config.workers),
            "-b",
            f"{config.host}:{config.port}",
            "-k",
            "uvicorn.workers.UvicornWorker",
            config.entry_point,
        ]

    def build_dev_command(self, config: ServerConfig) -> list[str]:
        return [
            "gunicorn",
            "-w",
            "1",
            "-b",
            f"{config.host}:{config.port}",
            "-k",
            "uvicorn.workers.UvicornWorker",
            "--reload",
            config.entry_point,
        ]

    def is_available(self) -> bool:
        return self.get_binary() is not None


class ServerRegistry:
    """Registry for server backends.

    Provides a pluggable way to add support for new server types.
    """

    _backends: dict[str, ServerBackend] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, backend: type[ServerBackend]) -> None:
        """Register a server backend class."""
        instance = backend()
        cls._backends[backend.name] = instance

    @classmethod
    def get(cls, name: str) -> ServerBackend | None:
        """Get a backend by name."""
        cls.register_defaults()
        return cls._backends.get(name)

    @classmethod
    def get_all(cls) -> dict[str, ServerBackend]:
        """Get all registered backends."""
        return cls._backends.copy()

    @classmethod
    def get_available(cls) -> list[ServerBackend]:
        """Get all available (installed) backends."""
        cls.register_defaults()
        return [b for b in cls._backends.values() if b.is_available()]

    @classmethod
    def get_default(cls) -> ServerBackend:
        """Get the default backend (first available)."""
        available = cls.get_available()
        if available:
            return available[0]
        return cls._backends["uvicorn"]

    @classmethod
    def register_defaults(cls) -> None:
        """Initialize default backends if not already done."""
        if not cls._initialized:
            cls.register(UvicornBackend)
            cls.register(HypercornBackend)
            cls.register(GranianBackend)
            cls.register(GunicornBackend)
            cls._initialized = True


class ServerManager:
    """Manager for running ASGI servers."""

    def __init__(self, backend: ServerBackend | str | None = None):
        if backend is None:
            self.backend = ServerRegistry.get_default()
        elif isinstance(backend, str):
            backend_instance = ServerRegistry.get(backend)
            if backend_instance is None:
                raise ValueError(f"Unknown server backend: {backend}")
            self.backend = backend_instance
        else:
            self.backend = backend

    def start(self, config: ServerConfig) -> None:
        """Start the server in production mode."""
        cmd = self.backend.build_start_command(config)
        env = os.environ.copy()
        env.update(config.env)
        env["LEX_ENV"] = "production"

        try:
            subprocess.run(cmd, env=env, check=False)
        except OSError as e:
            raise RuntimeError(f"Failed to start server: {e}") from e

    def start_dev(self, config: ServerConfig) -> None:
        """Start the server in development mode."""
        config.reload = True
        cmd = self.backend.build_dev_command(config)
        env = os.environ.copy()
        env.update(config.env)
        env["LEX_ENV"] = "development"

        try:
            subprocess.run(cmd, env=env, check=False)
        except OSError as e:
            raise RuntimeError(f"Failed to start dev server: {e}") from e


def discover_entry_point() -> str | None:
    """Discover application entry point from common locations."""
    candidates = [
        Path("src/main.py"),
        Path("main.py"),
        Path("app.py"),
        Path("src/app.py"),
    ]

    src_path = Path("src")
    if src_path.exists():
        candidates.extend(src_path.rglob("main.py"))
        candidates.extend(src_path.rglob("app.py"))

    for c in candidates:
        if c.exists():
            return str(c)
    return None


__all__ = [
    "GranianBackend",
    "GunicornBackend",
    "HypercornBackend",
    "ServerBackend",
    "ServerConfig",
    "ServerManager",
    "ServerRegistry",
    "UvicornBackend",
    "discover_entry_point",
]
