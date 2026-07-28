# tests/conftest.py
from pathlib import Path
import sys
import os

# Provide minimal stubs for optional external dependencies used in tests
import types

if "ollama" not in sys.modules:
    _ollama = types.ModuleType("ollama")

    class AsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def chat(self, *args, **kwargs):
            raise NotImplementedError

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def list(self):
            return {"models": []}

        def pull(self, model_name: str):
            return None

        def generate(self, *args, **kwargs):
            return {
                "model": kwargs.get("model", ""),
                "message": {"content": "", "role": "assistant"},
            }

    _ollama.AsyncClient = AsyncClient
    _ollama.Client = Client
    sys.modules["ollama"] = _ollama

import pytest

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None


@pytest.fixture(scope="session", autouse=True)
def _setup_test_env() -> None:
    """Set up test environment variables required for test fixtures."""
    # Set a dummy OpenAI API key for test fixture initialization
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "sk-test-key-for-fixtures"


try:
    import importlib

    importlib.import_module("lexigram.testing.fixtures.core")
    importlib.import_module("lexigram.testing.fixtures.ai")
except ImportError:
    pass


@ pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
async def test_bed():
    """Async TestBed fixture for testing."""
    from lexigram.testing import TestEnvironment

    bed = TestEnvironment()
    async with bed.context():
        yield bed
