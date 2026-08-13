# tests/conftest.py
import os
from pathlib import Path
import sys

import pytest

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

# Resolve dependencies via uv workspace
import importlib
import importlib.util

# Some tests expect `strawberry` to be importable. Provide a minimal stub
# implementation when the real dependency isn't installed so tests can patch
# its members without requiring installation.
try:
    import importlib

    importlib.import_module("strawberry")
except (ImportError, ModuleNotFoundError):
    import types

    strawberry_mod = types.ModuleType("strawberry")

    # Simple ID alias
    class ID(str):
        pass

    def type_decorator(arg=None, **_kwargs):
        if arg is None:

            def deco(cls):
                return cls

            return deco
        return arg

    federation_mod = types.ModuleType("strawberry.federation")

    class Schema:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    def fed_type(**_kwargs):
        def deco(cls):
            return cls

        return deco

    def fed_field(**_kwargs):
        def deco(func):
            return func

        return deco

    federation_mod.Schema = Schema
    federation_mod.type = fed_type
    federation_mod.field = fed_field

    strawberry_mod.ID = ID
    strawberry_mod.type = type_decorator
    strawberry_mod.federation = federation_mod

    import sys

    sys.modules["strawberry"] = strawberry_mod
    sys.modules["strawberry.federation"] = federation_mod


# Load core testing fixtures
try:
    import importlib

    importlib.import_module("lexigram.testing.fixtures.core")
except ImportError:
    pass

from lexigram.testing import TestEnvironment


@ pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
async def test_bed():
    """Async TestBed fixture for testing."""
    bed = TestEnvironment()
    async with bed.context():
        yield bed
