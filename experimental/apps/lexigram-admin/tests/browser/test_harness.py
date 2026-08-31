"""The browser harness itself must work, independent of any browser.

The server fixture is the part most likely to rot silently: if it stopped
binding or stopped tearing down, every browser test would skip or hang and
look like an environment problem. These tests exercise it over plain HTTP
so a machine without browser binaries still verifies the harness.
"""

from __future__ import annotations

import socket
from typing import Any
import pytest
from urllib.request import urlopen

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


def _echo_app(message: str) -> Starlette:
    async def index(request: Any) -> PlainTextResponse:
        return PlainTextResponse(message)

    return Starlette(routes=[Route("/", index)])


class TestLiveServer:
    """The fixture owns the full server lifecycle."""

    def test_serves_the_supplied_app(self, live_server: Any) -> None:
        base = live_server(_echo_app("hello from the harness"))

        with urlopen(f"{base}/", timeout=10) as response:
            body = response.read().decode()

        assert body == "hello from the harness"

    def test_binds_an_ephemeral_port(self, live_server: Any) -> None:
        """Hardcoded ports collide under parallel runs; port 0 does not."""
        base = live_server(_echo_app("x"))

        port = int(base.rsplit(":", 1)[1])

        assert port > 1024

    def test_two_apps_get_distinct_ports(self, live_server: Any) -> None:
        first = live_server(_echo_app("first"))
        second = live_server(_echo_app("second"))

        assert first != second
        with urlopen(f"{second}/", timeout=10) as response:
            assert response.read().decode() == "second"


def test_server_is_torn_down() -> None:
    """A leaked server would hold its port after the test that started it.

    Verified by running the fixture in-process and asserting the port stops
    accepting connections once the fixture's teardown has run.
    """
    import threading
    import time

    uvicorn = pytest.importorskip(
        "uvicorn", reason="uvicorn is required to serve browser tests"
    )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])

    config = uvicorn.Config(
        _echo_app("bye"), host="127.0.0.1", port=port, log_level="warning"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                break
        except OSError:
            time.sleep(0.05)

    server.should_exit = True
    thread.join(timeout=10)

    assert not thread.is_alive()
