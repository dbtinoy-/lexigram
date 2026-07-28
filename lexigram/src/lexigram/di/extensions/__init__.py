"""DI extension points — discovery, interceptors, strategies, and protocol validation."""

from __future__ import annotations

from lexigram.di.extensions.discovery import ProviderScanner
from lexigram.di.extensions.interceptors import (
    DIInterceptor,
    InterceptorRegistry,
    wrap_with_interceptors,
)
from lexigram.di.extensions.strategies import ResolutionStrategy
from lexigram.di.extensions.validator import ProtocolValidator, validate_protocol

__all__ = [
    "DIInterceptor",
    "InterceptorRegistry",
    "ProtocolValidator",
    "ProviderScanner",
    "ResolutionStrategy",
    "validate_protocol",
    "wrap_with_interceptors",
]
