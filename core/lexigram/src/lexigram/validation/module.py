"""Validation module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.di.module import DynamicModule, Module, module


@module()
class ValidationModule(Module):
    """Composable validation pipeline for the Lexigram Framework.

    Validation is a zero-dependency utility package — it has no DI provider
    and requires no IoC registration. This module exists for IoC graph
    completeness and future extensibility.

    Usage::

        from lexigram.validation import ValidationModule, ValidatorImpl

        # Direct use (no DI needed):
        validator = ValidatorImpl().rule("email", required(), email_format())
        result = validator.validate(data)
    """

    @classmethod
    def configure(cls) -> DynamicModule:
        """Return a DynamicModule for IoC registration.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` with no providers.
        """
        return DynamicModule(
            module=cls,
            providers=[],
            exports=[],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return a test-safe DynamicModule for IoC registration."""
        return cls.configure()


__all__ = ["ValidationModule"]
