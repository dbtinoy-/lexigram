"""Regression tests for the pymongo import guard in the MongoDB backend."""

from __future__ import annotations

import builtins
import importlib

import pytest

BACKEND_MODULE = "lexigram.nosql.backends.mongodb.backend"
COLLECTION_MODULE = "lexigram.nosql.backends.mongodb.collection"


@pytest.mark.parametrize("module_name", [BACKEND_MODULE, COLLECTION_MODULE])
def test_mongodb_modules_import_without_pymongo(
    module_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "pymongo" or name.startswith("pymongo."):
            raise ImportError(f"blocked import: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    module = importlib.import_module(module_name)
    importlib.reload(module)

    assert module.pymongo is None
