"""Dependency injection system for Lexigram Framework.

Provides the IoC container, builder, scoping, module system, provider
orchestrator, and DI decorators for constructor injection.

Exports:
    Container, Scope: Core DI container and scope.
    ContainerBuilder: Fluent API for building a configured container.
    ContainerRegistrarProtocol: Write-only container interface for Provider.register().
    ContainerResolverProtocol: Read-only container interface for Provider.boot().
    Module, module: DI module descriptor and decorator.
    Provider: Base class for all framework providers.
    ProviderOrchestrator: Coordinates provider lifecycle in priority order.
    ProviderPriority: Enum for provider registration priority.
    ResolutionStrategy: Extension hook for custom resolution logic.
    ServiceScope: Enum for singleton/scoped/transient lifetimes.
    Injectable, inject, injectable, scoped, singleton, transient: DI decorators.
"""

from __future__ import annotations

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.contracts.core.provider import ProviderPriority
    from lexigram.contracts.core.scopes import ServiceScope
    from lexigram.di.builder import ContainerBuilder
    from lexigram.di.container import Container, Scope
    from lexigram.di.context import (
        ModuleContextTokens,
        check_visibility,
        clear_module_context,
        get_current_module,
        set_module_context,
    )
    from lexigram.di.decorators import (
        Injectable,
        inject,
        injectable,
        scoped,
        singleton,
        transient,
    )
    from lexigram.di.extensions.strategies import ResolutionStrategy
    from lexigram.di.function_provider import FunctionProvider, provide
    from lexigram.di.markers import named
    from lexigram.di.module import Module, module
    from lexigram.di.orchestrator import ProviderOrchestrator
    from lexigram.di.provider import Provider

_LAZY_IMPORTS: dict[str, str] = {
    "ContainerRegistrarProtocol": "lexigram.contracts.core.di",
    "ContainerResolverProtocol": "lexigram.contracts.core.di",
    "ProviderPriority": "lexigram.contracts.core.provider",
    "Injectable": "lexigram.di.decorators",
    "inject": "lexigram.di.decorators",
    "injectable": "lexigram.di.decorators",
    "scoped": "lexigram.di.decorators",
    "singleton": "lexigram.di.decorators",
    "transient": "lexigram.di.decorators",
    "ContainerBuilder": "lexigram.di.builder",
    "Container": "lexigram.di.container",
    "Scope": "lexigram.di.container",
    "ResolutionStrategy": "lexigram.di.extensions.strategies",
    "FunctionProvider": "lexigram.di.function_provider",
    "provide": "lexigram.di.function_provider",
    "named": "lexigram.di.markers",
    "Module": "lexigram.di.module",
    "module": "lexigram.di.module",
    "ProviderOrchestrator": "lexigram.di.orchestrator",
    "Provider": "lexigram.di.provider",
    "ServiceScope": "lexigram.types",
    # types
    "ProviderState": "lexigram.di.types",
    # constants
    "DEFAULT_MAX_RESOLUTION_DEPTH": "lexigram.di.constants",
    "DEFAULT_SCOPE_NAME": "lexigram.di.constants",
    # --- added by migration script ---
    "DiConfig": "lexigram.di.config.models",
    "CircularDependencyError": "lexigram.di.exceptions",
    "ContainerBuildError": "lexigram.di.exceptions",
    "ContainerError": "lexigram.di.exceptions",
    "DependencyError": "lexigram.di.exceptions",
    "ModuleError": "lexigram.di.exceptions",
    "ProviderError": "lexigram.di.exceptions",
    "RegistrationError": "lexigram.di.exceptions",
    "UnresolvableDependencyError": "lexigram.di.exceptions",
    "DiProvider": "lexigram.di.integration.provider",
    # context
    "ModuleContextTokens": "lexigram.di.context",
    "check_visibility": "lexigram.di.context",
    "clear_module_context": "lexigram.di.context",
    "get_current_module": "lexigram.di.context",
    "set_module_context": "lexigram.di.context",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        mod = importlib.import_module(_LAZY_IMPORTS[name])
        return getattr(mod, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return list(_LAZY_IMPORTS.keys())


__all__ = list(_LAZY_IMPORTS.keys())
