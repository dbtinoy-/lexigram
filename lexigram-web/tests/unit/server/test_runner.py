"""Tests for server runner module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestRunServer:
    """Test suite for run_server function."""

    def test_creates_granian_with_correct_parameters(self) -> None:
        """run_server creates Granian instance with correct parameters."""
        mock_app = MagicMock()
        mock_granian_cls = MagicMock()
        mock_granian_instance = MagicMock()
        mock_granian_cls.return_value = mock_granian_instance
        mock_interfaces = MagicMock()
        mock_interfaces.ASGI = "asgi"

        # Create a mock granian module
        mock_granian_module = MagicMock()
        mock_granian_module.Granian = mock_granian_cls
        mock_constants_module = MagicMock()
        mock_constants_module.Interfaces = mock_interfaces

        import sys

        with patch.dict(
            "sys.modules",
            {
                "granian": mock_granian_module,
                "granian.constants": mock_constants_module,
            },
        ):
            # Clear the runner module cache to force re-import
            if "lexigram.web.server.runner" in sys.modules:
                del sys.modules["lexigram.web.server.runner"]

            from lexigram.web.server.runner import run_server

            run_server(mock_app, host="127.0.0.1", port=9000, workers=2)

        # Verify Granian was instantiated with correct args
        mock_granian_cls.assert_called_once()
        call_args = mock_granian_cls.call_args
        assert call_args[0][0] is mock_app  # app is first positional arg
        assert call_args[1]["address"] == "127.0.0.1"
        assert call_args[1]["port"] == 9000
        assert call_args[1]["workers"] == 2

        # Verify serve() was called
        mock_granian_instance.serve.assert_called_once()

    def test_uses_default_host_and_port(self) -> None:
        """run_server uses default host and port when not specified."""
        mock_app = MagicMock()
        mock_granian_cls = MagicMock()
        mock_granian_instance = MagicMock()
        mock_granian_cls.return_value = mock_granian_instance
        mock_interfaces = MagicMock()
        mock_interfaces.ASGI = "asgi"

        mock_granian_module = MagicMock()
        mock_granian_module.Granian = mock_granian_cls
        mock_constants_module = MagicMock()
        mock_constants_module.Interfaces = mock_interfaces

        import sys

        with patch.dict(
            "sys.modules",
            {
                "granian": mock_granian_module,
                "granian.constants": mock_constants_module,
            },
        ):
            if "lexigram.web.server.runner" in sys.modules:
                del sys.modules["lexigram.web.server.runner"]

            from lexigram.web.server.runner import run_server

            run_server(mock_app)

        call_args = mock_granian_cls.call_args
        assert call_args[1]["address"] == "127.0.0.1"
        assert call_args[1]["port"] == 8000

    def test_passes_extra_kwargs_to_granian(self) -> None:
        """run_server passes additional kwargs to Granian."""
        mock_app = MagicMock()
        mock_granian_cls = MagicMock()
        mock_granian_instance = MagicMock()
        mock_granian_cls.return_value = mock_granian_instance
        mock_interfaces = MagicMock()
        mock_interfaces.ASGI = "asgi"

        mock_granian_module = MagicMock()
        mock_granian_module.Granian = mock_granian_cls
        mock_constants_module = MagicMock()
        mock_constants_module.Interfaces = mock_interfaces

        import sys

        with patch.dict(
            "sys.modules",
            {
                "granian": mock_granian_module,
                "granian.constants": mock_constants_module,
            },
        ):
            if "lexigram.web.server.runner" in sys.modules:
                del sys.modules["lexigram.web.server.runner"]

            from lexigram.web.server.runner import run_server

            run_server(mock_app, host="0.0.0.0", port=8080, reload=True, workers=4)

        call_args = mock_granian_cls.call_args
        assert call_args[1]["reload"] is True
        assert call_args[1]["workers"] == 4

    def test_raises_import_error_when_granian_unavailable(self) -> None:
        """run_server raises ImportError with helpful message when Granian is unavailable."""
        mock_app = MagicMock()

        import sys

        # Remove granian from modules if it exists
        granian_modules = [k for k in sys.modules if k.startswith("granian")]
        removed = {k: sys.modules.pop(k) for k in granian_modules}

        try:
            # Now importing run_server should work, but calling it should fail
            from lexigram.web.server.runner import run_server

            with pytest.raises(ImportError, match="Granian is not installed"):
                run_server(mock_app)
        finally:
            # Restore modules
            sys.modules.update(removed)


__all__ = []
