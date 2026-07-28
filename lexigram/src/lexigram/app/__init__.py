"""Application runtime package for Lexigram Framework.

Entry-point for creating, starting, and stopping a Lexigram
:class:`Application`.  Lifecycle helper functions live in
:mod:`lexigram.app.runner`; the DI :class:`CoreProvider` lives in
:mod:`lexigram.app.di.provider`.

Exports:
    Application: The main application class.
    AppState: Application lifecycle state enum.
    run_application: Start, await OS signal, then stop.
    start_application: Start the application and its providers.
    stop_application: Gracefully stop the application.
"""

from __future__ import annotations

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.app.base import Application, AppState
    from lexigram.app.factory import create_app
    from lexigram.app.module import CoreModule
    from lexigram.app.pipeline import MiddlewarePipeline
    from lexigram.app.runner import (
        run_application,
        start_application,
        stop_application,
    )
    from lexigram.app.standard import StandardModule

_LAZY_IMPORTS: dict[str, str] = {
    "Application": "lexigram.app.base",
    "CoreModule": "lexigram.app.module",
    "StandardModule": "lexigram.app.standard",
    "create_app": "lexigram.app.factory",
    "run_application": "lexigram.app.runner",
    "start_application": "lexigram.app.runner",
    "stop_application": "lexigram.app.runner",
    # types
    "AppState": "lexigram.app.types",
    "ApplicationStarted": "lexigram.app.types",
    "ApplicationStarting": "lexigram.app.types",
    "ApplicationStopped": "lexigram.app.types",
    "ApplicationStopping": "lexigram.app.types",
    "HealthCheckCompleted": "lexigram.app.types",
    "ProviderBooted": "lexigram.app.types",
    "ProviderRegistered": "lexigram.app.types",
    # constants
    "DEFAULT_APP_NAME": "lexigram.app.constants",
    "DEFAULT_HEALTH_CHECK_TIMEOUT": "lexigram.app.constants",
    "DEFAULT_SHUTDOWN_TIMEOUT": "lexigram.app.constants",
    # protocols
    "AppLifecycleProtocol": "lexigram.app.protocols",
    # --- added by migration script ---
    "AppConfig": "lexigram.app.config.models",
    "AppError": "lexigram.app.exceptions",
    "AppShutdownError": "lexigram.app.exceptions",
    "AppStartupError": "lexigram.app.exceptions",
    "CoreProvider": "lexigram.app.di.provider",
    # pipeline
    "MiddlewarePipeline": "lexigram.app.pipeline",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return list(_LAZY_IMPORTS.keys())


__all__ = list(_LAZY_IMPORTS.keys())
