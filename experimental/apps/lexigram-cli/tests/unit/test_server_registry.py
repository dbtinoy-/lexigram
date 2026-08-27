"""Tests for ServerRegistry and server backend command construction."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lexigram.cli.registry.server import (
    GranianBackend,
    GunicornBackend,
    HypercornBackend,
    ServerConfig,
    ServerRegistry,
    UvicornBackend,
)


@pytest.fixture(autouse=True)
def reset_server_registry() -> None:
    """Reset ServerRegistry class state between tests."""
    original_backends = ServerRegistry._backends.copy()
    original_initialized = ServerRegistry._initialized
    yield
    ServerRegistry._backends = original_backends
    ServerRegistry._initialized = original_initialized


class TestServerConfig:
    def test_default_host_and_port(self) -> None:
        cfg = ServerConfig(entry_point="app:app")
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 8000

    def test_env_defaults_to_empty_dict(self) -> None:
        cfg = ServerConfig(entry_point="app:app")
        assert cfg.env == {}

    def test_custom_values(self) -> None:
        cfg = ServerConfig(entry_point="main:app", host="0.0.0.0", port=9000, workers=4)
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 9000
        assert cfg.workers == 4


class TestUvicornBackend:
    """build_start_command and build_dev_command for Uvicorn."""

    def test_start_command_basic(self) -> None:
        backend = UvicornBackend()
        cfg = ServerConfig(entry_point="app:app", host="127.0.0.1", port=8000)
        cmd = backend.build_start_command(cfg)
        assert cmd[0] == "uvicorn"
        assert "app:app" in cmd
        assert "--host" in cmd
        assert "127.0.0.1" in cmd
        assert "--port" in cmd
        assert "8000" in cmd

    def test_start_command_with_workers(self) -> None:
        backend = UvicornBackend()
        cfg = ServerConfig(entry_point="app:app", workers=4)
        cmd = backend.build_start_command(cfg)
        assert "--workers" in cmd
        assert "4" in cmd

    def test_start_command_no_workers_arg_for_single_worker(self) -> None:
        backend = UvicornBackend()
        cfg = ServerConfig(entry_point="app:app", workers=1)
        cmd = backend.build_start_command(cfg)
        assert "--workers" not in cmd

    def test_start_command_with_factory(self) -> None:
        backend = UvicornBackend()
        cfg = ServerConfig(entry_point="app:create_app", factory=True)
        cmd = backend.build_start_command(cfg)
        assert "--factory" in cmd

    def test_dev_command_includes_reload(self) -> None:
        backend = UvicornBackend()
        cfg = ServerConfig(entry_point="app:app")
        cmd = backend.build_dev_command(cfg)
        assert "--reload" in cmd

    def test_dev_command_does_not_include_workers(self) -> None:
        backend = UvicornBackend()
        cfg = ServerConfig(entry_point="app:app", workers=4)
        cmd = backend.build_dev_command(cfg)
        assert "--workers" not in cmd

    def test_name_is_uvicorn(self) -> None:
        assert UvicornBackend.name == "uvicorn"


class TestHypercornBackend:
    """build_start_command and build_dev_command for Hypercorn."""

    def test_start_command_uses_bind(self) -> None:
        backend = HypercornBackend()
        cfg = ServerConfig(entry_point="app:app", host="0.0.0.0", port=9000)
        cmd = backend.build_start_command(cfg)
        assert cmd[0] == "hypercorn"
        assert "--bind" in cmd
        assert "0.0.0.0:9000" in cmd
        assert "app:app" in cmd

    def test_start_command_with_workers(self) -> None:
        backend = HypercornBackend()
        cfg = ServerConfig(entry_point="app:app", workers=2)
        cmd = backend.build_start_command(cfg)
        assert "--workers" in cmd
        assert "2" in cmd

    def test_dev_command_includes_reload(self) -> None:
        backend = HypercornBackend()
        cfg = ServerConfig(entry_point="app:app")
        cmd = backend.build_dev_command(cfg)
        assert "--reload" in cmd

    def test_name_is_hypercorn(self) -> None:
        assert HypercornBackend.name == "hypercorn"


class TestGranianBackend:
    """build_start_command and build_dev_command for Granian."""

    def test_start_command_uses_asgi_interface(self) -> None:
        backend = GranianBackend()
        cfg = ServerConfig(entry_point="app:app", host="127.0.0.1", port=8000)
        cmd = backend.build_start_command(cfg)
        assert cmd[0] == "granian"
        assert "--interface" in cmd
        assert "asgi" in cmd
        assert "app:app" in cmd

    def test_start_command_host_and_port_present(self) -> None:
        backend = GranianBackend()
        cfg = ServerConfig(entry_point="app:app", host="0.0.0.0", port=7000)
        cmd = backend.build_start_command(cfg)
        assert "--host" in cmd
        assert "0.0.0.0" in cmd
        assert "--port" in cmd
        assert "7000" in cmd

    def test_start_command_with_workers(self) -> None:
        backend = GranianBackend()
        cfg = ServerConfig(entry_point="app:app", workers=3)
        cmd = backend.build_start_command(cfg)
        assert "--workers" in cmd
        assert "3" in cmd

    def test_dev_command_includes_reload(self) -> None:
        backend = GranianBackend()
        cfg = ServerConfig(entry_point="app:app")
        cmd = backend.build_dev_command(cfg)
        assert "--reload" in cmd

    def test_name_is_granian(self) -> None:
        assert GranianBackend.name == "granian"


class TestServerRegistry:
    """Registry operations and default registration."""

    def test_register_defaults_populates_all_four_backends(self) -> None:
        ServerRegistry._backends = {}
        ServerRegistry._initialized = False
        ServerRegistry.register_defaults()
        names = set(ServerRegistry._backends.keys())
        assert names == {"uvicorn", "hypercorn", "granian", "gunicorn"}

    def test_register_defaults_is_idempotent(self) -> None:
        ServerRegistry._backends = {}
        ServerRegistry._initialized = False
        ServerRegistry.register_defaults()
        ServerRegistry.register_defaults()  # second call is a no-op
        assert len(ServerRegistry._backends) == 4

    def test_get_returns_backend_by_name(self) -> None:
        ServerRegistry._backends = {}
        ServerRegistry._initialized = False
        backend = ServerRegistry.get("uvicorn")
        assert backend is not None
        assert backend.name == "uvicorn"

    def test_get_returns_none_for_unknown(self) -> None:
        ServerRegistry._backends = {}
        ServerRegistry._initialized = False
        ServerRegistry.register_defaults()
        assert ServerRegistry.get("nonexistent") is None

    def test_get_all_returns_copy(self) -> None:
        ServerRegistry._backends = {}
        ServerRegistry._initialized = False
        ServerRegistry.register_defaults()
        all_backends = ServerRegistry.get_all()
        assert len(all_backends) == 4
        # Modifying the copy must not affect the registry
        all_backends["injected"] = object()  # type: ignore[assignment]
        assert "injected" not in ServerRegistry._backends

    def test_register_custom_backend(self) -> None:
        ServerRegistry._backends = {}
        ServerRegistry._initialized = False

        class MyBackend(UvicornBackend):
            name = "my_backend"

        ServerRegistry.register(MyBackend)
        assert "my_backend" in ServerRegistry._backends

    def test_get_available_filters_unavailable(self) -> None:
        """is_available() == False backends are excluded from get_available()."""
        ServerRegistry._backends = {}
        ServerRegistry._initialized = False
        ServerRegistry.register_defaults()

        with patch.object(UvicornBackend, "is_available", return_value=True), \
             patch.object(HypercornBackend, "is_available", return_value=False), \
             patch.object(GranianBackend, "is_available", return_value=False), \
             patch.object(GunicornBackend, "is_available", return_value=False):
            available = ServerRegistry.get_available()

        assert len(available) == 1
        assert available[0].name == "uvicorn"
