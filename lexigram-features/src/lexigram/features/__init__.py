"""Feature flag subsystem for the Lexigram framework.

Provides a full-featured, async-first feature flag system with TTL caching,
runtime overrides, variant A/B testing, and DI integration.

Exports:
    Flag: Full flag definition including evaluation rules.
    FlagType: Evaluation strategy enum (BOOLEAN, PERCENTAGE, USER_LIST, etc.).
    FlagContext: Evaluation context (user ID, attributes, session).
    FlagEvaluation: Result of evaluating a flag for a given context.
    FlagValue: Type alias for boolean or variant-name evaluation result.
    FeatureFlagError: Base exception for all feature-flag errors.
    FlagNotFoundError: Raised when a requested flag does not exist.
    FlagEvaluationError: Raised when a provider fails during flag evaluation.
    FeatureFlagDisabledError: Raised when a feature-guarded path is called disabled.
    AbstractFlagProvider: Rich abstract base with full evaluation logic.
    LocalProvider: In-memory, code-defined flag store.
    EnvProvider: Reads flags from environment variables.
    ChainedProvider: Layered lookup across multiple providers.
    MemoryProvider: Lightweight test double with override support.
    FlagManager: Central manager with caching, overrides, and variant support.
    FlagChangeListener: Sync callback type for flag override change notifications.
    AsyncFlagChangeListener: Async callback type for flag override change notifications.
    ManagerConfig: Configuration dataclass for FlagManager.
    FeatureFlagsConfig: Runtime configuration for the DI provider.
    FeatureFlagsProvider: DI provider registering flag infrastructure.
    feature_flag: Decorator for async flag-gated functions.
    feature_flag_sync: Decorator for sync flag-gated functions.
    require_flag: Decorator that raises when a flag is disabled (async).
    require_flag_sync: Decorator that raises when a flag is disabled (sync).
    CacheBackendFlagProvider: Cache-backed flag provider (Redis, Memcached, etc.).
    FlagProviderProtocol: Contract for feature flag providers.
    MutableFlagProviderProtocol: Contract for mutable feature flag providers.
    FlagManagerProtocol: Contract for feature flag managers.
"""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# -- Version -------------------------------------------------------------------

from lexigram.features.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.features.backends.base import AbstractFlagProvider
    from lexigram.features.backends.cache import CacheBackendFlagProvider
    from lexigram.features.backends.chained import ChainedProvider
    from lexigram.features.backends.env import EnvProvider
    from lexigram.features.backends.local import LocalProvider
    from lexigram.features.backends.testing import MemoryProvider
    from lexigram.features.config import FeatureFlagsConfig
    from lexigram.features.decorators import (
        feature_flag,
        feature_flag_sync,
        require_flag,
        require_flag_sync,
    )
    from lexigram.features.di.provider import FeatureFlagsProvider
    from lexigram.features.events import FlagChangeEvent
    from lexigram.features.exceptions import (
        FeatureFlagDisabledError,
        FeatureFlagError,
        FlagEvaluationError,
        FlagNotFoundError,
    )
    from lexigram.features.manager import (
        AsyncFlagChangeListener,
        FlagChangeListener,
        FlagManager,
        ManagerConfig,
    )
    from lexigram.features.protocols import (
        FlagManagerProtocol,
        FlagProviderProtocol,
        MutableFlagProviderProtocol,
    )
    from lexigram.features.types import (
        Flag,
        FlagContext,
        FlagEvaluation,
        FlagType,
        FlagValue,
    )

_LAZY_IMPORTS: dict[str, str] = {
    # module
    "FeatureFlagsModule": "lexigram.features.module",
    # protocols
    "FlagProviderProtocol": "lexigram.features.protocols",
    "MutableFlagProviderProtocol": "lexigram.features.protocols",
    "FlagManagerProtocol": "lexigram.features.protocols",
    # types
    "Flag": "lexigram.features.types",
    "FlagContext": "lexigram.features.types",
    "FlagEvaluation": "lexigram.features.types",
    "FlagType": "lexigram.features.types",
    "FlagValue": "lexigram.features.types",
    # exceptions
    "FeatureFlagDisabledError": "lexigram.features.exceptions",
    "FeatureFlagError": "lexigram.features.exceptions",
    "FlagEvaluationError": "lexigram.features.exceptions",
    "FlagNotFoundError": "lexigram.features.exceptions",
    # backends
    "AbstractFlagProvider": "lexigram.features.backends.base",
    "CacheBackendFlagProvider": "lexigram.features.backends.cache",
    "LocalProvider": "lexigram.features.backends.local",
    "EnvProvider": "lexigram.features.backends.env",
    "ChainedProvider": "lexigram.features.backends.chained",
    "MemoryProvider": "lexigram.features.backends.testing",
    # manager
    "FlagManager": "lexigram.features.manager",
    "AsyncFlagChangeListener": "lexigram.features.manager",
    "FlagChangeListener": "lexigram.features.manager",
    "ManagerConfig": "lexigram.features.manager",
    # events
    "FlagChangeEvent": "lexigram.features.events",
    # decorators
    "feature_flag": "lexigram.features.decorators",
    "feature_flag_sync": "lexigram.features.decorators",
    "require_flag": "lexigram.features.decorators",
    "require_flag_sync": "lexigram.features.decorators",
    # config
    "FeatureFlagsConfig": "lexigram.features.config.models",
    # integration
    "FeatureFlagsProvider": "lexigram.features.di.provider",
    # Hooks
    "FeatureFlagEvaluatedHook": "lexigram.features.hooks",
    "FeatureFlagUpdatedHook": "lexigram.features.hooks",
}


def __getattr__(name: str) -> object:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS.keys())
