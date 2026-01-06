import importlib

import pytest


def test_importing_lexigram_runtime_raises():
    # After removing the compatibility shim, importing `lexigram.runtime` should fail
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("lexigram.runtime")


def test_core_submodules_available_directly():
    # Core functionality should be available directly under `lexigram` (no shim required)
    import lexigram.resilience as core_res
    import lexigram.testing as core_testing

    assert hasattr(core_res, "RetryConfig")

    # Basic shared API keys exist in core testing
    shared = set(getattr(core_testing, "__all__", []))
    assert "TestEnvironment" in shared or hasattr(core_testing, "TestEnvironment")
