"""Lexigram Core — Core framework primitives: builders, contexts, registries.

This module uses lazy imports for all public symbols to keep
import overhead minimal.  Every name listed in _LAZY_IMPORTS
is available at package level:

    from lexigram.primitives import <Symbol>

or by accessing the attribute on the package:

    import lexigram.primitives as core
    core.<Symbol>
"""

from __future__ import annotations

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.primitives.builder import (
        AbstractBuilder,
        buildable,
        builder_field,
    )
    from lexigram.primitives.context import (
        CAUSATION_ID,
        CORRELATION_ID,
        DEFAULT_KEYS,
        REQUEST_ID,
        REQUEST_METHOD,
        REQUEST_PATH,
        REQUEST_START_TIME,
        SPAN_ID,
        TENANT_ID,
        TRACE_FLAGS,
        TRACE_ID,
        USER_ID,
        Context,
        ContextKey,
        ContextVarRegistry,
        RequestContext,
        create_context_registry,
        create_default_context,
        get_request_context,
        propagate_context,
        request_scope,
        with_context,
    )
    from lexigram.primitives.pipeline import (
        PipelineContext,
        PipelineStep,
    )
    from lexigram.primitives.registry import (
        Registry,
        RegistryIntrospector,
        entry_point_catalog,
        on_register,
        on_unregister,
        registry_info,
    )

_LAZY_IMPORTS: dict[str, str] = {
    "AbstractBuilder": "lexigram.primitives.builder",
    "buildable": "lexigram.primitives.builder",
    "builder_field": "lexigram.primitives.builder",
    # context — keys
    "CAUSATION_ID": "lexigram.primitives.context",
    "CORRELATION_ID": "lexigram.primitives.context",
    "DEFAULT_KEYS": "lexigram.primitives.context",
    "REQUEST_ID": "lexigram.primitives.context",
    "REQUEST_METHOD": "lexigram.primitives.context",
    "REQUEST_PATH": "lexigram.primitives.context",
    "REQUEST_START_TIME": "lexigram.primitives.context",
    "SPAN_ID": "lexigram.primitives.context",
    "TENANT_ID": "lexigram.primitives.context",
    "TRACE_FLAGS": "lexigram.primitives.context",
    "TRACE_ID": "lexigram.primitives.context",
    "USER_ID": "lexigram.primitives.context",
    # clock
    "clock": "lexigram.primitives.clock",
    # context — classes
    "Context": "lexigram.primitives.context",
    "ContextKey": "lexigram.primitives.context",
    "ContextVarRegistry": "lexigram.primitives.context",
    "RequestContext": "lexigram.primitives.context",
    # context — factories & helpers
    "create_context_registry": "lexigram.primitives.context",
    "create_default_context": "lexigram.primitives.context",
    "get_request_context": "lexigram.primitives.context",
    "propagate_context": "lexigram.primitives.context",
    "request_scope": "lexigram.primitives.context",
    "with_context": "lexigram.primitives.context",
    # registry
    "Registry": "lexigram.primitives.registry",
    "on_register": "lexigram.primitives.registry",
    "on_unregister": "lexigram.primitives.registry",
    # registry introspection
    "RegistryIntrospector": "lexigram.primitives.registry.introspection",
    "entry_point_catalog": "lexigram.primitives.registry.introspection",
    "registry_info": "lexigram.primitives.registry.introspection",
    # exceptions
    "CoreError": "lexigram.primitives.exceptions",
    # constants
    "REQUEST_ID_KEY": "lexigram.primitives.constants",
    "TENANT_ID_KEY": "lexigram.primitives.constants",
    "TRACE_ID_KEY": "lexigram.primitives.constants",
    "SPAN_ID_KEY": "lexigram.primitives.constants",
    "USER_ID_KEY": "lexigram.primitives.constants",
    "REQUEST_PATH_KEY": "lexigram.primitives.constants",
    "REQUEST_METHOD_KEY": "lexigram.primitives.constants",
    "REQUEST_START_TIME_KEY": "lexigram.primitives.constants",
    # types
    "Priority": "lexigram.primitives.types",
    # protocols
    "Buildable": "lexigram.primitives.protocols",
    "Registrable": "lexigram.primitives.protocols",
    # pipeline
    "PipelineContext": "lexigram.primitives.pipeline",
    "PipelineStep": "lexigram.primitives.pipeline",
    "LazyImport": "lexigram.primitives.lazy",
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
__version__ = "0.1.0"
