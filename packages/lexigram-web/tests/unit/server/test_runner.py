"""Tests for server runner module."""

from __future__ import annotations

import sys
import threading
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class _FakeUvicorn:
    """Minimal uvicorn stand-in that records configs and serves immediately."""

    def __init__(self) -> None:
        self.configs: list[object] = []

    class Config:
        def __init__(self, app: object, host: str, port: int, **kwargs: object) -> None:
            self.app = app
            self.host = host
            self.port = port
            self.kwargs = kwargs

    class Server:
        def __init__(self, config: object) -> None:
            self.config = config

        async def serve(self) -> None:
            pass

    def make_module(self) -> Any:
        return SimpleNamespace(Config=self._record, Server=_FakeUvicorn.Server)

    def _record(self, app: object, host: str, port: int, **kwargs: object) -> object:
        config = _FakeUvicorn.Config(app, host, port, **kwargs)
        self.configs.append(config)
        return config


class TestRunServer:
    """Test suite for run_server function."""

    def test_creates_granian_with_correct_parameters(self) -> None:
        """String app: run_server creates Granian with correct parameters."""
        mock_granian_cls = MagicMock()
        mock_granian_instance = MagicMock()
        mock_granian_cls.return_value = mock_granian_instance
        mock_interfaces = MagicMock()
        mock_interfaces.ASGI = "asgi"

        mock_granian_module = MagicMock()
        mock_granian_module.Granian = mock_granian_cls
        mock_constants_module = MagicMock()
        mock_constants_module.Interfaces = mock_interfaces

        with patch.dict(
            "sys.modules",
            {
                "granian": mock_granian_module,
                "granian.constants": mock_constants_module,
            },
        ):
            from lexigram.web.server.runner import run_server

            run_server("module:app", host="127.0.0.1", port=9000, workers=2)

        mock_granian_cls.assert_called_once()
        call_args = mock_granian_cls.call_args
        assert call_args[0][0] == "module:app"
        assert call_args[1]["address"] == "127.0.0.1"
        assert call_args[1]["port"] == 9000
        assert call_args[1]["interface"] == "asgi"
        assert call_args[1]["workers"] == 2

        mock_granian_instance.serve.assert_called_once()

    def test_uses_default_host_and_port(self) -> None:
        """String app: run_server uses default host and port when not specified."""
        mock_granian_cls = MagicMock()
        mock_granian_instance = MagicMock()
        mock_granian_cls.return_value = mock_granian_instance
        mock_interfaces = MagicMock()
        mock_interfaces.ASGI = "asgi"

        mock_granian_module = MagicMock()
        mock_granian_module.Granian = mock_granian_cls
        mock_constants_module = MagicMock()
        mock_constants_module.Interfaces = mock_interfaces

        with patch.dict(
            "sys.modules",
            {
                "granian": mock_granian_module,
                "granian.constants": mock_constants_module,
            },
        ):
            from lexigram.web.server.runner import run_server

            run_server("module:app")

        call_args = mock_granian_cls.call_args
        assert call_args[1]["address"] == "127.0.0.1"
        assert call_args[1]["port"] == 8000

    def test_passes_extra_kwargs_to_granian(self) -> None:
        """String app: run_server passes additional kwargs to Granian."""
        mock_granian_cls = MagicMock()
        mock_granian_instance = MagicMock()
        mock_granian_cls.return_value = mock_granian_instance
        mock_interfaces = MagicMock()
        mock_interfaces.ASGI = "asgi"

        mock_granian_module = MagicMock()
        mock_granian_module.Granian = mock_granian_cls
        mock_constants_module = MagicMock()
        mock_constants_module.Interfaces = mock_interfaces

        with patch.dict(
            "sys.modules",
            {
                "granian": mock_granian_module,
                "granian.constants": mock_constants_module,
            },
        ):
            from lexigram.web.server.runner import run_server

            run_server("module:app", host="0.0.0.0", port=8080, reload=True, workers=4)

        call_args = mock_granian_cls.call_args
        assert call_args[1]["reload"] is True
        assert call_args[1]["workers"] == 4

    def test_raises_import_error_when_granian_unavailable(self) -> None:
        """String app: run_server raises ImportError when Granian is unavailable."""
        granian_modules = [k for k in sys.modules if k.startswith("granian")]
        removed = {k: sys.modules.pop(k) for k in granian_modules}

        try:
            from lexigram.web.server.runner import run_server

            with (
                patch.dict("sys.modules", {"granian": None, "granian.constants": None}),
                pytest.raises(ImportError, match="Granian is not installed"),
            ):
                run_server("module:app")
        finally:
            sys.modules.update(removed)

    def test_instance_uses_uvicorn(self) -> None:
        """App instance: run_server delegates to Uvicorn, never Granian."""
        mock_app = MagicMock()
        fake_uvicorn = _FakeUvicorn()

        def _run() -> None:
            with patch.dict("sys.modules", {"uvicorn": fake_uvicorn.make_module()}):
                from lexigram.web.server.runner import run_server

                run_server(mock_app, host="0.0.0.0", port=8080, workers=2)

        thread = threading.Thread(target=_run)
        thread.start()
        thread.join()

        assert len(fake_uvicorn.configs) == 1
        config = fake_uvicorn.configs[0]
        assert config.app is mock_app
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.kwargs == {"workers": 2}

    def test_instance_uses_default_host_and_port(self) -> None:
        """App instance: run_server defaults to 127.0.0.1:8000."""
        mock_app = MagicMock()
        mock_app.config = None
        fake_uvicorn = _FakeUvicorn()

        def _run() -> None:
            with patch.dict("sys.modules", {"uvicorn": fake_uvicorn.make_module()}):
                from lexigram.web.server.runner import run_server

                run_server(mock_app)

        thread = threading.Thread(target=_run)
        thread.start()
        thread.join()

        assert len(fake_uvicorn.configs) == 1
        config = fake_uvicorn.configs[0]
        assert config.host == "127.0.0.1"
        assert config.port == 8000
