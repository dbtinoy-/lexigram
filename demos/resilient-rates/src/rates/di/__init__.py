"""DI wiring for the resilient rates demo.

Convention followed: **Provider pattern** — ``RatesProvider`` is the
canonical provider shape, declaring bindings in ``register()`` and
resolving cross-module dependencies in ``boot()``.

Exports:

- ``RatesProvider`` — the demo's provider
"""

from __future__ import annotations

from rates.di.provider import RatesProvider

__all__ = ["RatesProvider"]
