"""Monitoring module.

This module provides monitoring and observability features
for GraphQL APIs, including metrics and tracing.
"""

from __future__ import annotations

from lexigram.graphql.monitoring.metrics import (
    GraphQLMetrics,
    MetricsCollectorProtocol,
    MetricsExtension,
)
from lexigram.graphql.monitoring.tracing import (
    TracingExtension,
    trace_resolver,
)

__all__ = [
    # Metrics
    "GraphQLMetrics",
    "MetricsCollectorProtocol",
    "MetricsExtension",
    # Tracing
    "TracingExtension",
    "trace_resolver",
]
