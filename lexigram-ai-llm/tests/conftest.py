"""Shared test configuration and fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow absolute imports like 'from support.mock_clients import ...'
sys.path.insert(0, str(Path(__file__).parent))

import pytest

from lexigram.ai.llm.registry.core import ProviderRegistry


@pytest.fixture(scope="module", autouse=True)
def _setup_test_env() -> None:
    """Set up test environment variables that are required for test fixtures.

    This fixture runs per test module and sets up environment variables
    needed by LLM client initialization during tests. The key is restored
    on teardown so it never leaks into other packages' tests.
    """
    # Set a dummy OpenAI API key for test fixture initialization
    # Tests that need specific keys or mocking should override this
    _previous = os.environ.get("OPENAI_API_KEY")
    if not _previous:
        os.environ["OPENAI_API_KEY"] = "sk-test-key-for-fixtures"
    yield
    if _previous is None:
        os.environ.pop("OPENAI_API_KEY", None)
    else:
        os.environ["OPENAI_API_KEY"] = _previous


@pytest.fixture
def provider_registry() -> ProviderRegistry:
    """Provide a fresh ProviderRegistry instance for each test.

    Returns:
        A new ProviderRegistry with all built-in providers registered.
    """
    return ProviderRegistry()
