"""Contract compliance test suites for Lexigram protocol implementations.

Each suite is a base test class.  Subclass it, implement the abstract
factory method, and pytest will run all contract checks automatically::

    class TestRedisCacheCompliance(CacheBackendCompliance):
        async def create_backend(self):
            return RedisCacheBackend("redis://localhost:6379/15")

Available suites:

- :class:`~lexigram.testing.compliance.AuditLoggerCompliance`
- :class:`~lexigram.testing.compliance.AuditStoreCompliance`
- :class:`~lexigram.testing.compliance.BlobStoreCompliance`
- :class:`~lexigram.testing.compliance.CacheBackendCompliance`
- :class:`~lexigram.testing.compliance.DatabaseProviderCompliance`
- :class:`~lexigram.testing.compliance.DistributedLockCompliance`
- :class:`~lexigram.testing.compliance.EventBusCompliance`
- :class:`~lexigram.testing.compliance.FlagProviderCompliance`
- :class:`~lexigram.testing.compliance.MiddlewareCompliance`
- :class:`~lexigram.testing.compliance.NotificationChannelCompliance`
- :class:`~lexigram.testing.compliance.QueueBackendCompliance`
- :class:`~lexigram.testing.compliance.RepositoryCompliance`
- :class:`~lexigram.testing.compliance.SearchEngineCompliance`
- :class:`~lexigram.testing.compliance.TaskQueueCompliance`
- :class:`~lexigram.testing.compliance.VectorStoreCompliance`
- :class:`~lexigram.testing.compliance.WebhookDeliveryStoreCompliance`
- :class:`~lexigram.testing.compliance.WebhookSubscriptionStoreCompliance`
"""

from __future__ import annotations

from lexigram.testing.compliance.audit import (
    AuditLoggerCompliance,
    AuditStoreCompliance,
)
from lexigram.testing.compliance.blob_store import BlobStoreCompliance
from lexigram.testing.compliance.cache import CacheBackendCompliance
from lexigram.testing.compliance.database import DatabaseProviderCompliance
from lexigram.testing.compliance.distributed_lock import DistributedLockCompliance
from lexigram.testing.compliance.event_bus import EventBusCompliance
from lexigram.testing.compliance.flags import FlagProviderCompliance
from lexigram.testing.compliance.middleware import MiddlewareCompliance
from lexigram.testing.compliance.notification import NotificationChannelCompliance
from lexigram.testing.compliance.queue_backend import QueueBackendCompliance
from lexigram.testing.compliance.repository import RepositoryCompliance
from lexigram.testing.compliance.search import SearchEngineCompliance
from lexigram.testing.compliance.secrets import (
    StoreConformanceSuite,
    parametrize_rotatable_store,
)
from lexigram.testing.compliance.task_queue import TaskQueueCompliance
from lexigram.testing.compliance.vector_store import VectorStoreCompliance
from lexigram.testing.compliance.webhook import (
    WebhookDeliveryStoreCompliance,
    WebhookSubscriptionStoreCompliance,
)

__all__ = [
    "AuditLoggerCompliance",
    "AuditStoreCompliance",
    "BlobStoreCompliance",
    "CacheBackendCompliance",
    "DatabaseProviderCompliance",
    "DistributedLockCompliance",
    "EventBusCompliance",
    "FlagProviderCompliance",
    "MiddlewareCompliance",
    "NotificationChannelCompliance",
    "QueueBackendCompliance",
    "RepositoryCompliance",
    "SearchEngineCompliance",
    "StoreConformanceSuite",
    "TaskQueueCompliance",
    "VectorStoreCompliance",
    "WebhookDeliveryStoreCompliance",
    "WebhookSubscriptionStoreCompliance",
    "parametrize_rotatable_store",
]
