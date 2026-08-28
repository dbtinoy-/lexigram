"""Pytest plugin for Lexigram Framework.

This plugin is automatically loaded by pytest via entry points when lexigram-testing
is installed in the environment.
"""

from __future__ import annotations

# Export core fixtures so they are automatically available in all tests
pytest_plugins = [
    "lexigram.testing.fixtures.core",
    "lexigram.testing.fixtures.ai",
    "lexigram.testing.fixtures.db",
    "lexigram.testing.fixtures.messaging",
    "lexigram.testing.fixtures.web",
    "lexigram.testing.fixtures.tasks",
    "lexigram.testing.integration.fixtures",
]
