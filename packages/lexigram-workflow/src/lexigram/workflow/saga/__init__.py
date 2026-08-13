"""SagaProtocol orchestration primitives for lexigram-workflow."""

from __future__ import annotations

from lexigram.contracts.workflow.protocols import SagaState, SagaStoreProtocol
from lexigram.contracts.workflow.steps import SagaStepError
from lexigram.workflow.saga.base import AbstractSaga, SagaError, SagaStep
from lexigram.workflow.saga.batch import SagaBatchProcessor
from lexigram.workflow.saga.content_addressed import (
    ContentAddressedSaga,
    ContentAddressedStage,
)
from lexigram.workflow.saga.hooks import (
    SagaCompensationCompletedHook,
    SagaCompensationContext,
    SagaCompensationTriggeredHook,
    SagaStepContext,
    SagaStepExecutedHook,
    SagaStepFailedHook,
)

__all__ = [
    "AbstractSaga",
    "ContentAddressedSaga",
    "ContentAddressedStage",
    "SagaBatchProcessor",
    "SagaCompensationCompletedHook",
    "SagaCompensationContext",
    "SagaCompensationTriggeredHook",
    "SagaError",
    "SagaState",
    "SagaStep",
    "SagaStepContext",
    "SagaStepError",
    "SagaStepExecutedHook",
    "SagaStepFailedHook",
    "SagaStoreProtocol",
]
