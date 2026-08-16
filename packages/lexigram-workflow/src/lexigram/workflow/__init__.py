"""Workflow orchestration package for Lexigram Framework.

Provides pipeline execution, transformation pipes, bulk operations,
saga coordination, and directed-graph workflow execution.
"""

from __future__ import annotations

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

import importlib
import importlib.metadata
from typing import TYPE_CHECKING, Any

from lexigram.workflow.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.workflow.bulk.models import (
        BulkBatchResult,
        BulkItemError,
        BulkOperationMetrics,
        BulkOperationState,
    )
    from lexigram.workflow.bulk.operation import BulkOperation
    from lexigram.workflow.checkpoint.store_cache import CacheContentCheckpointStore
    from lexigram.workflow.checkpoint.store_database import (
        DatabaseContentCheckpointStore,
    )
    from lexigram.workflow.checkpoint.store_memory import InMemoryContentCheckpointStore
    from lexigram.workflow.config import (
        BulkOperationConfig,
        ContentCheckpointConfig,
        GraphConfig,
    )
    from lexigram.workflow.core.definition import WorkflowDefinition
    from lexigram.workflow.core.instance import WorkflowInstance
    from lexigram.workflow.core.pipe import TransformPipe
    from lexigram.workflow.decorators import saga_step, workflow
    from lexigram.workflow.di.provider import WorkflowProvider
    from lexigram.workflow.exceptions import (
        BulkOperationCancelledError,
        BulkOperationError,
        BulkOperationTimeoutError,
        CycleDetectedError,
        GraphExecutionError,
        GraphTimeoutError,
        GraphValidationError,
        HumanInputRequiredError,
        NodeExecutionError,
        PipelineExecutionError,
        PipelineStepError,
        WorkflowCompensationError,
        WorkflowError,
        WorkflowNotFoundError,
        WorkflowStateError,
        WorkflowStepError,
        WorkflowTimeoutError,
        WorkflowVersionMismatchError,
    )
    from lexigram.workflow.execution.checkpoint import WorkflowCheckpoint
    from lexigram.workflow.execution.history import ExecutionHistory
    from lexigram.workflow.execution.runner import WorkflowRunner
    from lexigram.workflow.graph.builder import WorkflowBuilder
    from lexigram.workflow.graph.edge import WorkflowEdge
    from lexigram.workflow.graph.engine import WorkflowEngine
    from lexigram.workflow.graph.node import AbstractWorkflowNode, NodeType
    from lexigram.workflow.graph.state import WorkflowState
    from lexigram.workflow.module import WorkflowModule
    from lexigram.workflow.nodes.agent_node import AgentNode
    from lexigram.workflow.nodes.gate_node import GateNode
    from lexigram.workflow.nodes.human_node import HumanNode
    from lexigram.workflow.nodes.llm_node import LLMNode
    from lexigram.workflow.nodes.subworkflow_node import SubworkflowNode
    from lexigram.workflow.nodes.tool_node import ToolNode
    from lexigram.workflow.pipeline import (
        ConditionalStep,
        FunctionStep,
        ParallelStep,
        Pipeline,
        PipelineContext,
        PipelineStep,
        conditional,
        parallel,
        pipeline_step,
        step,
    )
    from lexigram.workflow.saga import (
        AbstractSaga,
        ContentAddressedSaga,
        ContentAddressedStage,
    )
    from lexigram.workflow.types import GraphResult, NodeResult

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Bulk
    "BulkOperation": ("lexigram.workflow.bulk.operation", "BulkOperation"),
    "BulkBatchResult": ("lexigram.workflow.bulk.models", "BulkBatchResult"),
    "BulkItemError": ("lexigram.workflow.bulk.models", "BulkItemError"),
    "BulkOperationMetrics": ("lexigram.workflow.bulk.models", "BulkOperationMetrics"),
    "BulkOperationState": ("lexigram.workflow.bulk.models", "BulkOperationState"),
    # Pipeline
    "TransformPipe": ("lexigram.workflow.core.pipe", "TransformPipe"),
    # Core
    "WorkflowDefinition": ("lexigram.workflow.core.definition", "WorkflowDefinition"),
    "WorkflowInstance": ("lexigram.workflow.core.instance", "WorkflowInstance"),
    "ConditionalStep": ("lexigram.workflow.pipeline", "ConditionalStep"),
    "FunctionStep": ("lexigram.workflow.pipeline", "FunctionStep"),
    "ParallelStep": ("lexigram.workflow.pipeline", "ParallelStep"),
    "Pipeline": ("lexigram.workflow.pipeline", "Pipeline"),
    "PipelineContext": ("lexigram.workflow.pipeline", "PipelineContext"),
    "PipelineStep": ("lexigram.workflow.pipeline", "PipelineStep"),
    "conditional": ("lexigram.workflow.pipeline", "conditional"),
    "parallel": ("lexigram.workflow.pipeline", "parallel"),
    "pipeline_step": ("lexigram.workflow.pipeline", "pipeline_step"),
    "step": ("lexigram.workflow.pipeline", "step"),
    # SagaProtocol
    "AbstractSaga": ("lexigram.workflow.saga", "AbstractSaga"),
    "ContentAddressedSaga": ("lexigram.workflow.saga", "ContentAddressedSaga"),
    "ContentAddressedStage": ("lexigram.workflow.saga", "ContentAddressedStage"),
    # Types
    "SagaStep": ("lexigram.workflow.types", "SagaStep"),
    "StepExecutionResult": ("lexigram.workflow.types", "StepExecutionResult"),
    "StepStatus": ("lexigram.workflow.types", "StepStatus"),
    # Graph types
    "NodeResult": ("lexigram.workflow.types", "NodeResult"),
    "GraphResult": ("lexigram.workflow.types", "GraphResult"),
    # Graph config
    "GraphConfig": ("lexigram.workflow.config", "GraphConfig"),
    "BulkOperationConfig": ("lexigram.workflow.config", "BulkOperationConfig"),
    "ContentCheckpointConfig": ("lexigram.workflow.config", "ContentCheckpointConfig"),
    # Exceptions (existing)
    "BulkOperationCancelledError": (
        "lexigram.workflow.exceptions",
        "BulkOperationCancelledError",
    ),
    "BulkOperationError": ("lexigram.workflow.exceptions", "BulkOperationError"),
    "BulkOperationTimeoutError": (
        "lexigram.workflow.exceptions",
        "BulkOperationTimeoutError",
    ),
    "PipelineExecutionError": (
        "lexigram.workflow.exceptions",
        "PipelineExecutionError",
    ),
    "PipelineStepError": ("lexigram.workflow.exceptions", "PipelineStepError"),
    "WorkflowError": ("lexigram.workflow.exceptions", "WorkflowError"),
    "WorkflowNotFoundError": (
        "lexigram.workflow.exceptions",
        "WorkflowNotFoundError",
    ),
    "WorkflowStateError": ("lexigram.workflow.exceptions", "WorkflowStateError"),
    "WorkflowStepError": ("lexigram.workflow.exceptions", "WorkflowStepError"),
    "WorkflowTimeoutError": (
        "lexigram.workflow.exceptions",
        "WorkflowTimeoutError",
    ),
    "WorkflowCompensationError": (
        "lexigram.workflow.exceptions",
        "WorkflowCompensationError",
    ),
    # Graph exceptions
    "GraphExecutionError": ("lexigram.workflow.exceptions", "GraphExecutionError"),
    "NodeExecutionError": ("lexigram.workflow.exceptions", "NodeExecutionError"),
    "CycleDetectedError": ("lexigram.workflow.exceptions", "CycleDetectedError"),
    "GraphTimeoutError": ("lexigram.workflow.exceptions", "GraphTimeoutError"),
    "GraphValidationError": ("lexigram.workflow.exceptions", "GraphValidationError"),
    "HumanInputRequiredError": (
        "lexigram.workflow.exceptions",
        "HumanInputRequiredError",
    ),
    "WorkflowVersionMismatchError": (
        "lexigram.workflow.exceptions",
        "WorkflowVersionMismatchError",
    ),
    # Graph engine
    "WorkflowEngine": ("lexigram.workflow.graph.engine", "WorkflowEngine"),
    "WorkflowBuilder": ("lexigram.workflow.graph.builder", "WorkflowBuilder"),
    "WorkflowState": ("lexigram.workflow.graph.state", "WorkflowState"),
    "WorkflowEdge": ("lexigram.workflow.graph.edge", "WorkflowEdge"),
    "AbstractWorkflowNode": ("lexigram.workflow.graph.node", "AbstractWorkflowNode"),
    "NodeType": ("lexigram.workflow.graph.node", "NodeType"),
    # Nodes
    "AgentNode": ("lexigram.workflow.nodes.agent_node", "AgentNode"),
    "LLMNode": ("lexigram.workflow.nodes.llm_node", "LLMNode"),
    "ToolNode": ("lexigram.workflow.nodes.tool_node", "ToolNode"),
    "HumanNode": ("lexigram.workflow.nodes.human_node", "HumanNode"),
    "GateNode": ("lexigram.workflow.nodes.gate_node", "GateNode"),
    "SubworkflowNode": ("lexigram.workflow.nodes.subworkflow_node", "SubworkflowNode"),
    # Execution
    "WorkflowRunner": ("lexigram.workflow.execution.runner", "WorkflowRunner"),
    "WorkflowCheckpoint": (
        "lexigram.workflow.execution.checkpoint",
        "WorkflowCheckpoint",
    ),
    "ExecutionHistory": ("lexigram.workflow.execution.history", "ExecutionHistory"),
    # Checkpoint
    "InMemoryContentCheckpointStore": (
        "lexigram.workflow.checkpoint.store_memory",
        "InMemoryContentCheckpointStore",
    ),
    "CacheContentCheckpointStore": (
        "lexigram.workflow.checkpoint.store_cache",
        "CacheContentCheckpointStore",
    ),
    "DatabaseContentCheckpointStore": (
        "lexigram.workflow.checkpoint.store_database",
        "DatabaseContentCheckpointStore",
    ),
    # Decorators
    "workflow": ("lexigram.workflow.decorators", "workflow"),
    "saga_step": ("lexigram.workflow.decorators", "saga_step"),
    # DI
    "WorkflowModule": ("lexigram.workflow.module", "WorkflowModule"),
    "WorkflowProvider": ("lexigram.workflow.di.provider", "WorkflowProvider"),
    # Events
    "WorkflowStartedEvent": ("lexigram.workflow.events", "WorkflowStartedEvent"),
    "WorkflowCompletedEvent": ("lexigram.workflow.events", "WorkflowCompletedEvent"),
    "WorkflowFailedEvent": ("lexigram.workflow.events", "WorkflowFailedEvent"),
    # Hooks
    "WorkflowCompletedHook": ("lexigram.workflow.hooks", "WorkflowCompletedHook"),
    "WorkflowStartedHook": ("lexigram.workflow.hooks", "WorkflowStartedHook"),
    "WorkflowStateTransitionedHook": (
        "lexigram.workflow.hooks",
        "WorkflowStateTransitionedHook",
    ),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "AbstractSaga",
    "AbstractWorkflowNode",
    "AgentNode",
    "BulkBatchResult",
    "BulkItemError",
    "BulkOperation",
    "BulkOperationCancelledError",
    "BulkOperationConfig",
    "BulkOperationError",
    "BulkOperationMetrics",
    "BulkOperationState",
    "BulkOperationTimeoutError",
    "CacheContentCheckpointStore",
    "ConditionalStep",
    "ContentAddressedSaga",
    "ContentAddressedStage",
    "ContentCheckpointConfig",
    "CycleDetectedError",
    "DatabaseContentCheckpointStore",
    "ExecutionHistory",
    "FunctionStep",
    "GateNode",
    "GraphConfig",
    "GraphExecutionError",
    "GraphResult",
    "GraphTimeoutError",
    "GraphValidationError",
    "HumanInputRequiredError",
    "HumanNode",
    "InMemoryContentCheckpointStore",
    "LLMNode",
    "NodeExecutionError",
    "NodeResult",
    "NodeType",
    "ParallelStep",
    "Pipeline",
    "PipelineContext",
    "PipelineExecutionError",
    "PipelineStep",
    "PipelineStepError",
    "SagaStep",
    "StepExecutionResult",
    "StepStatus",
    "SubworkflowNode",
    "ToolNode",
    "TransformPipe",
    "WorkflowBuilder",
    "WorkflowCheckpoint",
    "WorkflowCompensationError",
    "WorkflowCompletedEvent",
    "WorkflowCompletedHook",
    "WorkflowDefinition",
    "WorkflowEdge",
    "WorkflowEngine",
    "WorkflowError",
    "WorkflowFailedEvent",
    "WorkflowInstance",
    "WorkflowModule",
    "WorkflowNotFoundError",
    "WorkflowProvider",
    "WorkflowRunner",
    "WorkflowStartedEvent",
    "WorkflowStartedHook",
    "WorkflowState",
    "WorkflowStateError",
    "WorkflowStateTransitionedHook",
    "WorkflowStepError",
    "WorkflowTimeoutError",
    "WorkflowVersionMismatchError",
    "conditional",
    "parallel",
    "pipeline_step",
    "saga_step",
    "step",
    "workflow",
]
