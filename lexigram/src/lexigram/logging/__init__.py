"""Structured, context-aware logging for Lexigram Framework.

Fully structlog-based logging pipeline with no stdlib logging dependencies.
Configuration driven by ``LoggingConfig`` and applied via ``configure_logging``.

Exports:
    get_logger: Factory for obtaining a structured logger bound to a module.
    configure_logging: Apply ``LoggingConfig`` to the active pipeline.
    apply_config: Low-level configuration application.
    LoggerFactoryProtocol, LoggerFactoryImpl: Factory classes for logger creation.
    LoggerProtocol: Protocol for structured loggers.
    Logger: Alias for ``LoggerProtocol``.
    QueryLogEntry, QueryLoggerProtocol: Database query log contracts.
    CRITICAL, DEBUG, ERROR, INFO, WARNING: Log-level name constants.
"""

from __future__ import annotations

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.logging import LoggerFactoryProtocol, LoggerProtocol
    from lexigram.contracts.data.sql.query_log import QueryLogEntry, QueryLoggerProtocol
    from lexigram.logging.config.models import LoggingConfig as LoggingConfig
    from lexigram.logging.configurator import (
        apply_config,
        configure_logging,
        reset_logging,
    )
    from lexigram.logging.constants import CRITICAL, DEBUG, ERROR, INFO, WARNING
    from lexigram.logging.factory import (
        LoggerFactoryImpl,
        get_logger,
    )
    from lexigram.logging.types import LogLevel as LogLevel

_LAZY_IMPORTS: dict[str, str] = {
    # contracts
    "LoggerProtocol": "lexigram.contracts.core.logging",
    "QueryLogEntry": "lexigram.contracts.data.sql.query_log",
    "QueryLoggerProtocol": "lexigram.contracts.data.sql.query_log",
    # config
    "apply_config": "lexigram.logging.configurator",
    "configure_logging": "lexigram.logging.configurator",
    "reset_logging": "lexigram.logging.configurator",
    # factory
    "LoggerFactoryImpl": "lexigram.logging.factory",
    "LoggerFactoryProtocol": "lexigram.contracts.core.logging",
    "get_logger": "lexigram.logging.factory",
    # constants
    "CRITICAL": "lexigram.logging.constants",
    "DEBUG": "lexigram.logging.constants",
    "ERROR": "lexigram.logging.constants",
    "INFO": "lexigram.logging.constants",
    "WARNING": "lexigram.logging.constants",
    # types
    "LogLevel": "lexigram.logging.types",
    # config model
    "LoggingConfig": "lexigram.logging.config.models",
    # provider
    "LoggingProvider": "lexigram.logging.di.provider",
}

# Logger is a public alias for LoggerProtocol (same module, different attr name).
_ALIASED_IMPORTS: dict[str, tuple[str, str]] = {
    "Logger": ("lexigram.contracts.core.logging", "LoggerProtocol"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _ALIASED_IMPORTS:
        import importlib

        module_path, attr = _ALIASED_IMPORTS[name]
        value = getattr(importlib.import_module(module_path), attr)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return list(_LAZY_IMPORTS.keys()) + list(_ALIASED_IMPORTS.keys())


__all__ = list(_LAZY_IMPORTS.keys()) + list(_ALIASED_IMPORTS.keys())
