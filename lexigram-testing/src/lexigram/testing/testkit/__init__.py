"""Lightweight test utilities for unit testing Lexigram services.

Provides zero-dependency helpers for unit tests — no extension packages
required.

Exports:
    TestEnvironment: Pre-wired container with in-memory fakes for unit tests.
    FakeRepository, FakeEventBus, FakeCommandBus, FakeQueryBus,
    FakeAuditLogger, FakeLock, FakeOutbox, FakeUoW: Test-friendly aliases for memory fakes.
    assert_ok, assert_err, assert_err_type, assert_err_contains: Result helpers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.testing.testkit.assertions import (
        assert_err,
        assert_err_contains,
        assert_err_type,
        assert_ok,
    )
    from lexigram.testing.testkit.environment import TestEnvironment
    from lexigram.testing.testkit.fakes import (
        FakeAuditLogger,
        FakeCommandBus,
        FakeEventBus,
        FakeLock,
        FakeOutbox,
        FakeQueryBus,
        FakeRepository,
        FakeUoW,
    )

_LAZY_IMPORTS: dict[str, str] = {
    # Environment
    "TestEnvironment": "lexigram.testing.testkit.environment",
    # Fakes
    "FakeAuditLogger": "lexigram.testing.testkit.fakes",
    "FakeCommandBus": "lexigram.testing.testkit.fakes",
    "FakeEventBus": "lexigram.testing.testkit.fakes",
    "FakeLock": "lexigram.testing.testkit.fakes",
    "FakeOutbox": "lexigram.testing.testkit.fakes",
    "FakeQueryBus": "lexigram.testing.testkit.fakes",
    "FakeRepository": "lexigram.testing.testkit.fakes",
    "FakeUoW": "lexigram.testing.testkit.fakes",
    # Assertions
    "assert_err": "lexigram.testing.testkit.assertions",
    "assert_err_contains": "lexigram.testing.testkit.assertions",
    "assert_err_type": "lexigram.testing.testkit.assertions",
    "assert_ok": "lexigram.testing.testkit.assertions",
}


def __getattr__(name: str) -> object:
    """Lazily import and return a public attribute by name."""
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    """Return list of public API names."""
    return list(_LAZY_IMPORTS.keys())


__all__ = list(_LAZY_IMPORTS.keys())
