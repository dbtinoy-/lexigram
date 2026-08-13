"""AI Evaluation framework for Lexigram.

Provides evaluators, a harness, and reproducible experiment tracking:
seed-stable run ids, metric/error streams, digest-verified checkpoints,
ablation comparisons, and error analysis for completed runs.
"""

from __future__ import annotations

from lexigram.ai.evaluation.ablation import AblationRunner
from lexigram.ai.evaluation.analysis import ErrorAnalysis
from lexigram.ai.evaluation.checkpoints import FileCheckpointStore
from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.ai.evaluation.constants import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_THRESHOLD,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RETRIES,
)
from lexigram.ai.evaluation.di.provider import EvaluationProvider
from lexigram.ai.evaluation.exceptions import (
    AblationError,
    AnalysisError,
    CheckpointError,
    DatasetError,
    EvaluationConfigError,
    EvaluatorNotFoundError,
    HarnessError,
    TrackingError,
)
from lexigram.ai.evaluation.module import EvaluationModule
from lexigram.ai.evaluation.tracking import LocalTracker, make_run_id
from lexigram.ai.evaluation.types import (
    BatchEvaluationResult,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRunContext,
    EvaluationSample,
    RunReport,
)
from lexigram.contracts.ai.experiment import (
    AblationResult,
    AnalysisReport,
    Checkpoint,
    CheckpointStoreProtocol,
    ErrorRecord,
    ExperimentConfig,
    ExperimentRun,
    ExperimentTrackerProtocol,
    MetricRecord,
    RunStatus,
)

__all__ = [
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_THRESHOLD",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_RETRIES",
    "AblationError",
    "AblationResult",
    "AblationRunner",
    "AnalysisError",
    "AnalysisReport",
    "BatchEvaluationResult",
    "Checkpoint",
    "CheckpointError",
    "CheckpointStoreProtocol",
    "DatasetError",
    "ErrorAnalysis",
    "ErrorRecord",
    "EvaluationConfig",
    "EvaluationConfigError",
    "EvaluationDataset",
    "EvaluationModule",
    "EvaluationProvider",
    "EvaluationResult",
    "EvaluationRunContext",
    "EvaluationSample",
    "EvaluatorNotFoundError",
    "ExperimentConfig",
    "ExperimentRun",
    "ExperimentTrackerProtocol",
    "FileCheckpointStore",
    "HarnessError",
    "LocalTracker",
    "MetricRecord",
    "RunReport",
    "RunStatus",
    "TrackingError",
    "make_run_id",
]
