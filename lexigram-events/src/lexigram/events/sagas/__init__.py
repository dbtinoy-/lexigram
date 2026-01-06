"""SagaProtocol orchestration — SagaBase, SagaStep, SagaManagerProtocol, InMemorySagaStore.

A saga coordinates multi-step distributed transactions with compensation on failure.
"""

from __future__ import annotations

from lexigram.events.sagas.base import SagaBase, SagaStep, saga_step
from lexigram.events.sagas.context import SagaContext, SagaStepResult
from lexigram.events.sagas.manager import SagaManagerProtocol
from lexigram.events.sagas.sql import SqlSagaStore
from lexigram.events.sagas.store import InMemorySagaStore, SagaStore
from lexigram.events.sagas.types import (
    SagaRecord,
    SagaStatus,
    SagaStepRecord,
    SagaStepStatus,
)

__all__ = [
    "InMemorySagaStore",
    "SagaBase",
    "SagaContext",
    "SagaManagerProtocol",
    "SagaRecord",
    "SagaStatus",
    "SagaStep",
    "SagaStepRecord",
    "SagaStepResult",
    "SagaStepStatus",
    "SagaStore",
    "SqlSagaStore",
    "saga_step",
]
