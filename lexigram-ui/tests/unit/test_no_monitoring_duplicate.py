"""Verify monitoring/ duplicate shim directory has been deleted."""

from __future__ import annotations

import os


def test_monitoring_directory_deleted() -> None:
    monitoring_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "src",
        "lexigram",
        "ui",
        "monitoring",
    )
    assert not os.path.exists(os.path.normpath(monitoring_path)), (
        "lexigram/ui/monitoring/ still exists — delete it (it is a duplicate of performance/)"
    )


def test_performance_symbols_still_importable_after_deletion() -> None:
    from lexigram.ui.performance.performance import (
        RenderCache,
        RequestCoalescer,
        ResponseOptimizer,
        add_htmx_timing_header,
        cached_render,
        debounced_search_attrs,
        infinite_scroll_trigger,
        lazy_load_placeholder,
        measure_render_time,
        optimize_htmx_response,
    )
    from lexigram.ui.performance.observability import (
        MetricProtocol,
        MetricsCollector,
        MetricType,
    )
    assert RenderCache is not None
    assert MetricsCollector is not None
