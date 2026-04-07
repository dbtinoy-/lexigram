"""E2E test configuration.

All tests in this directory are tagged ``@pytest.mark.e2e`` and require a
running ASGI server + full framework stack.  They are skipped by default and
only run when the ``--run-e2e`` flag is explicitly passed:

    uv run pytest --run-e2e lexigram-admin/tests/e2e/

"""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: end-to-end tests (skipped unless --run-e2e)")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-e2e", default=False):
        skip_e2e = pytest.mark.skip(reason="E2E tests skipped: pass --run-e2e to enable")
        for item in items:
            if item.get_closest_marker("e2e"):
                item.add_marker(skip_e2e)


def pytest_addoption(parser):
    parser.addoption("--run-e2e", action="store_true", default=False, help="Run e2e tests")
