"""Tests for UI observability module."""

import pytest

from lexigram.ui.performance import observability


class TestMetricType:
    """Tests for MetricType enum."""

    def test_counter_type(self) -> None:
        """Test counter metric type."""
        assert observability.MetricType.COUNTER.value == "counter"

    def test_histogram_type(self) -> None:
        """Test histogram metric type."""
        assert observability.MetricType.HISTOGRAM.value == "histogram"

    def test_gauge_type(self) -> None:
        """Test gauge metric type."""
        assert observability.MetricType.GAUGE.value == "gauge"


class TestMetricProtocol:
    """Tests for MetricProtocol."""

    def test_metric_creation(self) -> None:
        """Test metric protocol creation."""
        metric = observability.MetricProtocol(
            name="test.metric",
            value=1.0,
            type=observability.MetricType.COUNTER,
        )
        assert metric.name == "test.metric"
        assert metric.value == 1.0

    def test_metric_with_labels(self) -> None:
        """Test metric with labels."""
        metric = observability.MetricProtocol(
            name="test.metric",
            value=1.0,
            type=observability.MetricType.COUNTER,
            labels={"env": "test"},
        )
        assert metric.labels["env"] == "test"

    def test_metric_default_timestamp(self) -> None:
        """Test default timestamp is set."""
        metric = observability.MetricProtocol(
            name="test.metric",
            value=1.0,
            type=observability.MetricType.COUNTER,
        )
        assert metric.timestamp > 0


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_collector_initializes(self) -> None:
        """Test collector can be instantiated."""
        collector = observability.MetricsCollector()
        assert collector is not None

    def test_inc_counter(self) -> None:
        """Test increment counter."""
        collector = observability.MetricsCollector()
        collector.inc("requests")
        assert collector.get_counter("requests") == 1

    def test_inc_counter_with_value(self) -> None:
        """Test increment counter by custom value."""
        collector = observability.MetricsCollector()
        collector.inc("requests", 5)
        assert collector.get_counter("requests") == 5

    def test_inc_counter_multiple(self) -> None:
        """Test multiple increments."""
        collector = observability.MetricsCollector()
        collector.inc("requests")
        collector.inc("requests")
        collector.inc("requests")
        assert collector.get_counter("requests") == 3

    def test_inc_with_labels(self) -> None:
        """Test increment with labels."""
        collector = observability.MetricsCollector()
        collector.inc("requests", labels={"method": "GET"})
        collector.inc("requests", labels={"method": "POST"})
        assert collector.get_counter("requests", {"method": "GET"}) == 1
        assert collector.get_counter("requests", {"method": "POST"}) == 1

    def test_observe_histogram(self) -> None:
        """Test histogram observation."""
        collector = observability.MetricsCollector()
        collector.observe("request_duration", 10.5)
        collector.observe("request_duration", 20.5)
        stats = collector.get_histogram_stats("request_duration")
        assert stats["count"] == 2
        assert stats["sum"] == 31.0

    def test_observe_histogram_stats(self) -> None:
        """Test histogram statistics."""
        collector = observability.MetricsCollector()
        collector.observe("latency", 10)
        collector.observe("latency", 20)
        collector.observe("latency", 30)
        stats = collector.get_histogram_stats("latency")
        assert stats["count"] == 3
        assert stats["avg"] == 20
        assert stats["min"] == 10
        assert stats["max"] == 30

    def test_set_gauge(self) -> None:
        """Test gauge setting."""
        collector = observability.MetricsCollector()
        collector.set("memory_usage", 1024.5)
        assert collector.get_gauge("memory_usage") == 1024.5

    def test_set_gauge_with_labels(self) -> None:
        """Test gauge with labels."""
        collector = observability.MetricsCollector()
        collector.set("memory_usage", 512, labels={"host": "server1"})
        collector.set("memory_usage", 1024, labels={"host": "server2"})
        assert collector.get_gauge("memory_usage", {"host": "server1"}) == 512
        assert collector.get_gauge("memory_usage", {"host": "server2"}) == 1024

    def test_get_counter_nonexistent(self) -> None:
        """Test get counter for nonexistent metric."""
        collector = observability.MetricsCollector()
        assert collector.get_counter("nonexistent") == 0

    def test_get_gauge_nonexistent(self) -> None:
        """Test get gauge for nonexistent metric."""
        collector = observability.MetricsCollector()
        assert collector.get_gauge("nonexistent") == 0

    def test_get_histogram_stats_empty(self) -> None:
        """Test histogram stats for nonexistent."""
        collector = observability.MetricsCollector()
        stats = collector.get_histogram_stats("nonexistent")
        assert stats["count"] == 0

    def test_reset(self) -> None:
        """Test reset clears all metrics."""
        collector = observability.MetricsCollector()
        collector.inc("requests")
        collector.observe("latency", 10)
        collector.set("memory", 1024)
        collector.reset()
        assert collector.get_counter("requests") == 0
        assert collector.get_histogram_stats("latency")["count"] == 0
        assert collector.get_gauge("memory") == 0

    def test_to_dict(self) -> None:
        """Test export to dictionary."""
        collector = observability.MetricsCollector()
        collector.inc("requests")
        collector.observe("latency", 10)
        collector.set("memory", 1024)
        result = collector.to_dict()
        assert "counters" in result
        assert "histograms" in result
        assert "gauges" in result


class TestMakeKey:
    """Tests for metric key creation."""

    def test_make_key_no_labels(self) -> None:
        """Test key without labels."""
        collector = observability.MetricsCollector()
        key = collector._make_key("test")
        assert key == "test"

    def test_make_key_with_labels(self) -> None:
        """Test key with labels."""
        collector = observability.MetricsCollector()
        key = collector._make_key("test", {"a": "1", "b": "2"})
        assert key == "test{a=1,b=2}"


class TestObservabilityExports:
    """Tests for observability module exports."""

    def test_metric_protocol_exported(self) -> None:
        """Test MetricProtocol is exported."""
        from lexigram.ui.performance import observability

        assert hasattr(observability, "MetricProtocol")

    def test_metric_type_exported(self) -> None:
        """Test MetricType is exported."""
        from lexigram.ui.performance import observability

        assert hasattr(observability, "MetricType")

    def test_collector_exported(self) -> None:
        """Test collector is exported."""
        from lexigram.ui.performance import observability

        assert hasattr(observability, "MetricsCollector")

    def test_all_exports(self) -> None:
        """Test __all__ contains expected items."""
        from lexigram.ui.performance import observability

        assert "MetricProtocol" in observability.__all__
        assert "MetricType" in observability.__all__
        assert "MetricsCollector" in observability.__all__