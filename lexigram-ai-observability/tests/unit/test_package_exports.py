"""Tests for the package __init__.py exports."""

import pytest

import lexigram.ai.observability
from lexigram.ai.observability import constants, exceptions, hooks, protocols


class TestPackageExports:
    """Verify package exports are available."""

    def test_constants_import(self):
        from lexigram.ai.observability.constants import (
            DEFAULT_CHECK_INTERVAL_SECONDS,
            DEFAULT_CHECK_TIMEOUT_SECONDS,
        )
        assert DEFAULT_CHECK_INTERVAL_SECONDS == 30
        assert DEFAULT_CHECK_TIMEOUT_SECONDS == 5.0

    def test_version_available(self):
        from lexigram.ai.observability.constants import __version__
        assert __version__ is not None

    def test_env_prefix_constant(self):
        from lexigram.ai.observability.constants import ENV_PREFIX
        assert ENV_PREFIX == "LEX_AI_OBSERVABILITY__"

    def test_metric_prefixes(self):
        from lexigram.ai.observability.constants import (
            METRIC_PREFIX_LLM,
            METRIC_PREFIX_VECTOR,
            METRIC_PREFIX_EMBEDDING,
        )
        assert METRIC_PREFIX_LLM == "lexigram.ai.llm"
        assert METRIC_PREFIX_VECTOR == "lexigram.ai.vector"
        assert METRIC_PREFIX_EMBEDDING == "lexigram.ai.embedding"

    def test_span_names(self):
        from lexigram.ai.observability.constants import (
            SPAN_LLM_CALL,
            SPAN_VECTOR_QUERY,
            SPAN_EMBEDDING_GENERATE,
            SPAN_RAG_PIPELINE,
        )
        assert SPAN_LLM_CALL == "llm.call"
        assert SPAN_VECTOR_QUERY == "vector.query"


class TestObservabilityExports:
    """Verify observability module exports."""

    def test_trace_decorators_available(self):
        from lexigram.ai.observability import trace_llm, trace_rag, trace_vector

        assert callable(trace_llm)
        assert callable(trace_rag)
        assert callable(trace_vector)

    def test_track_decorators_available(self):
        from lexigram.ai.observability import (
            track_embedding_operation,
            track_llm_call,
            track_vector_operation,
        )

        assert callable(track_embedding_operation)
        assert callable(track_llm_call)
        assert callable(track_vector_operation)

    def test_exceptions_available(self):
        from lexigram.ai.observability.exceptions import (
            ObservabilityError,
            HealthCheckError,
            MetricsError,
            TracingError,
        )

        assert issubclass(ObservabilityError, Exception)
        assert issubclass(HealthCheckError, ObservabilityError)
        assert issubclass(MetricsError, ObservabilityError)
        assert issubclass(TracingError, ObservabilityError)


class TestHooksExported:
    """Verify hooks are exported."""

    def test_hooks_exported(self):
        from lexigram.ai.observability.hooks import (
            AIObservabilityStartedHook,
            HealthCheckRunHook,
            LLMCallTracedHook,
        )

        assert AIObservabilityStartedHook is not None
        assert HealthCheckRunHook is not None
        assert LLMCallTracedHook is not None


class TestProtocolsExported:
    """Verify protocols are exported."""

    def test_protocols_exist(self):
        from lexigram.ai.observability.protocols import (
            AIHealthMonitorProtocol,
            AIMetricsProtocol,
            AITracerProtocol,
            ObservabilityProtocol,
        )

        assert AIHealthMonitorProtocol is not None
        assert AIMetricsProtocol is not None
        assert AITracerProtocol is not None
        assert ObservabilityProtocol is not None


class TestSubmoduleExports:
    """Verify submodules are exported."""

    def test_metrics_submodule(self):
        from lexigram.ai.observability.metrics import AIMetrics

        assert AIMetrics is not None

    def test_tracing_submodule(self):
        from lexigram.ai.observability.tracing import AITracer

        assert AITracer is not None

    def test_health_submodule(self):
        from lexigram.ai.observability.health import AIHealthMonitor

        assert AIHealthMonitor is not None

    def test_config_module(self):
        from lexigram.ai.observability.config import ObservabilityConfig

        assert ObservabilityConfig is not None