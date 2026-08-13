"""DI resolution engine — descriptors, registry, resolver, injector, and type hints."""

from __future__ import annotations

from lexigram.di.resolution.context import current_resolver_var, get_resolver
from lexigram.di.resolution.descriptor import ServiceDescriptor
from lexigram.di.resolution.injector import DependencyInjector
from lexigram.di.resolution.registry import ServiceRegistry
from lexigram.di.resolution.resolver import ServiceResolver
from lexigram.di.resolution.store import ServiceStore
from lexigram.di.resolution.type_hints import BoundedCache, TypeHintResolverImpl
from lexigram.di.resolution.validator import GraphValidator

__all__ = [
    "BoundedCache",
    "DependencyInjector",
    "GraphValidator",
    "ServiceDescriptor",
    "ServiceRegistry",
    "ServiceResolver",
    "ServiceStore",
    "TypeHintResolverImpl",
    "current_resolver_var",
    "get_resolver",
]
