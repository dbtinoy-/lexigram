"""A11y test configuration.

All tests in this directory require a real browser and are skipped unless
``--run-a11y`` is passed:

    uv run pytest --run-a11y lexigram-ui/tests/a11y/

"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_GALLERY_PATH = pathlib.Path(__file__).parent / "gallery.py"


def _load_gallery_module() -> object:
    """Load tests/a11y/gallery.py without requiring 'tests' to be a package."""
    spec = importlib.util.spec_from_file_location("a11y_gallery", _GALLERY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def gallery() -> dict[str, str]:
    """Render every component to a full HTML page, light theme."""
    return _load_gallery_module().build_gallery()


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the --run-a11y flag."""
    parser.addoption(
        "--run-a11y",
        action="store_true",
        default=False,
        help="Run accessibility tests (requires Playwright browsers)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip a11y tests unless --run-a11y is passed."""
    if config.getoption("--run-a11y", default=False):
        return
    skip_a11y = pytest.mark.skip(reason="A11y tests skipped: pass --run-a11y")
    for item in items:
        if "a11y" in item.nodeid:
            item.add_marker(skip_a11y)