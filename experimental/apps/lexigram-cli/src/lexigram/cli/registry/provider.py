"""Provider registry for the add command.

This module provides a registry pattern for Lexigram providers/packages.
The catalog of built-in providers lives in ``provider_catalog`` and the
registry/installer plumbing in ``provider_registry``; both are re-exported
here so the public import paths are unchanged.
"""

from __future__ import annotations

from lexigram.cli.registry.provider_catalog import (
    AdminProvider as AdminProvider,
)
from lexigram.cli.registry.provider_catalog import (
    AIProvider as AIProvider,
)
from lexigram.cli.registry.provider_catalog import (
    AuthProvider as AuthProvider,
)
from lexigram.cli.registry.provider_catalog import (
    CacheProvider as CacheProvider,
)
from lexigram.cli.registry.provider_catalog import (
    CommonProvider as CommonProvider,
)
from lexigram.cli.registry.provider_catalog import (
    ConnectProvider as ConnectProvider,
)
from lexigram.cli.registry.provider_catalog import (
    DatabaseService as DatabaseService,
)
from lexigram.cli.registry.provider_catalog import (
    EventsProvider as EventsProvider,
)
from lexigram.cli.registry.provider_catalog import (
    GraphQLProvider as GraphQLProvider,
)
from lexigram.cli.registry.provider_catalog import (
    MessagingProvider as MessagingProvider,
)
from lexigram.cli.registry.provider_catalog import (
    MonitoringProvider as MonitoringProvider,
)
from lexigram.cli.registry.provider_catalog import (
    MonitorProvider as MonitorProvider,
)
from lexigram.cli.registry.provider_catalog import (
    NotificationProvider as NotificationProvider,
)
from lexigram.cli.registry.provider_catalog import (
    Provider as Provider,
)
from lexigram.cli.registry.provider_catalog import (
    ProviderInfo as ProviderInfo,
)
from lexigram.cli.registry.provider_catalog import (
    QueueProvider as QueueProvider,
)
from lexigram.cli.registry.provider_catalog import (
    ResilienceProvider as ResilienceProvider,
)
from lexigram.cli.registry.provider_catalog import (
    SearchProvider as SearchProvider,
)
from lexigram.cli.registry.provider_catalog import (
    StorageProvider as StorageProvider,
)
from lexigram.cli.registry.provider_catalog import (
    TasksProvider as TasksProvider,
)
from lexigram.cli.registry.provider_catalog import (
    TestingProvider as TestingProvider,
)
from lexigram.cli.registry.provider_catalog import (
    WebProvider as WebProvider,
)
from lexigram.cli.registry.provider_registry import (
    ProviderInstaller as ProviderInstaller,
)
from lexigram.cli.registry.provider_registry import (
    ProviderRegistry as ProviderRegistry,
)

__all__ = [
    "AIProvider",
    "AdminProvider",
    "AuthProvider",
    "CacheProvider",
    "CommonProvider",
    "ConnectProvider",
    "DatabaseService",
    "EventsProvider",
    "GraphQLProvider",
    "MessagingProvider",
    "MonitorProvider",
    "MonitoringProvider",
    "NotificationProvider",
    "Provider",
    "ProviderInfo",
    "ProviderInstaller",
    "ProviderRegistry",
    "QueueProvider",
    "ResilienceProvider",
    "SearchProvider",
    "StorageProvider",
    "TasksProvider",
    "TestingProvider",
    "WebProvider",
]
