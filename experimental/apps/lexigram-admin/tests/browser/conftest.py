"""Browser-test harness: a real server on an ephemeral port, plus Playwright.

The existing Playwright tests required an operator to start an admin server
by hand on a hardcoded port and silently skipped when nothing was listening,
so they never actually ran. This harness owns the server lifecycle instead:
it binds port 0, waits for readiness, and tears down afterwards, so browser
tests are self-contained and safe to run in parallel.

Every dependency is checked separately and reported with a specific skip
reason, because "playwright missing", "browser binary missing", and "server
failed to boot" need different fixes and must not look alike.

Enable with ``--run-browser``; the suite is skipped by default so a
contributor without browser binaries still gets a green run.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest

_STARTUP_TIMEOUT_S = 30.0
_POLL_INTERVAL_S = 0.05


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the opt-in flag for browser tests."""
    parser.addoption(
        "--run-browser",
        action="store_true",
        default=False,
        help="Run Playwright browser tests (requires installed browsers)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Declare the marker so strict-marker runs do not error."""
    config.addinivalue_line(
        "markers", "browser: browser test (skipped unless --run-browser)"
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip browser-marked tests unless explicitly enabled."""
    if config.getoption("--run-browser", default=False):
        return
    skip = pytest.mark.skip(reason="Browser tests skipped: pass --run-browser")
    for item in items:
        if item.get_closest_marker("browser"):
            item.add_marker(skip)


def _free_port() -> int:
    """Reserve an ephemeral port and release it for immediate reuse."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until_listening(host: str, port: int, timeout: float) -> bool:
    """Poll until *port* accepts connections or *timeout* elapses."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(_POLL_INTERVAL_S)
    return False


@pytest.fixture(scope="session")
def browser_type() -> Any:
    """Return a launched Chromium browser, or skip with a precise reason."""
    playwright_api = pytest.importorskip(
        "playwright.sync_api", reason="playwright is not installed"
    )

    with playwright_api.sync_playwright() as api:
        try:
            browser = api.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001 — reported as a skip, not a failure
            pytest.skip(
                "Chromium is not available. Run 'uv run playwright install "
                f"chromium'. Underlying error: {type(exc).__name__}"
            )
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def page(browser_type: Any) -> Iterator[Any]:
    """Return a page in a fresh context so tests never share cookies."""
    context = browser_type.new_context()
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()


@pytest.fixture
def live_server() -> Iterator[Any]:
    """Serve an ASGI app on an ephemeral port for the duration of a test.

    Yields a factory taking an ASGI application and returning its base URL,
    so each test supplies the app it needs.
    """
    uvicorn = pytest.importorskip(
        "uvicorn", reason="uvicorn is required to serve browser tests"
    )

    servers: list[Any] = []
    threads: list[threading.Thread] = []

    def _start(app: Any, host: str = "127.0.0.1") -> str:
        port = _free_port()
        config = uvicorn.Config(
            app, host=host, port=port, log_level="warning", lifespan="on"
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        servers.append(server)
        threads.append(thread)

        if not _wait_until_listening(host, port, _STARTUP_TIMEOUT_S):
            server.should_exit = True
            pytest.fail(f"Server did not start on {host}:{port}")
        return f"http://{host}:{port}"

    try:
        yield _start
    finally:
        for server in servers:
            server.should_exit = True
        for thread in threads:
            thread.join(timeout=10.0)
