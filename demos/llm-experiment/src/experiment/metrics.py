"""In-memory JSON metrics collector (counter/gauge/histogram)."""

from __future__ import annotations

from typing import Any

from lexigram.serialization import dumps_str


class JsonCounter:
    """A counter instrument that records into a deterministic JSON sink."""

    def __init__(self, name: str, sink: JsonMetricsCollector) -> None:
        self.name = name
        self._sink = sink

    def increment(
        self, amount: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        self._sink.increment(self.name, amount, labels)


class JsonHistogram:
    """A histogram instrument that records into a deterministic JSON sink."""

    def __init__(self, name: str, sink: JsonMetricsCollector) -> None:
        self.name = name
        self._sink = sink

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        self._sink.histogram(self.name, value, labels)


class JsonGauge:
    """A gauge instrument that records into a deterministic JSON sink."""

    def __init__(self, name: str, sink: JsonMetricsCollector) -> None:
        self.name = name
        self._sink = sink

    def set_value(self, value: float, labels: dict[str, str] | None = None) -> None:
        self._sink.gauge(self.name, value, labels)


class JsonMetricsCollector:
    """Minimal :class:`MetricsCollectorProtocol` that snapshots to JSON.

    Counters/histograms/gauge observations are keyed by ``name`` plus a
    canonical, sort-stable label key so identical inputs always produce
    identical snapshots (used by the reproducibility digest).
    """

    def __init__(self) -> None:
        self._counters: dict[tuple[str, str], float] = {}
        self._gauges: dict[tuple[str, str], float] = {}
        self._histograms: dict[tuple[str, str], list[float]] = {}

    @staticmethod
    def _labels_key(labels: dict[str, str] | None) -> str:
        if not labels:
            return "-"
        return dumps_str(labels, sort_keys=True)

    def increment(
        self, name: str, value: float = 1.0, tags: dict[str, str] | None = None
    ) -> None:
        key = (name, self._labels_key(tags))
        self._counters[key] = self._counters.get(key, 0.0) + value

    def gauge(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        key = (name, self._labels_key(tags))
        self._gauges[key] = value

    def histogram(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        key = (name, self._labels_key(tags))
        self._histograms.setdefault(key, []).append(value)

    def create_counter(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
    ) -> JsonCounter:
        return JsonCounter(name, self)

    def create_gauge(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
    ) -> JsonGauge:
        return JsonGauge(name, self)

    def create_histogram(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        buckets: list[float] | None = None,
    ) -> JsonHistogram:
        return JsonHistogram(name, self)

    def snapshot(self) -> dict[str, Any]:
        """Return a deterministically ordered JSON-ready snapshot."""
        out: dict[str, Any] = {"counters": {}, "gauges": {}, "histograms": {}}
        for (name, labels), total in sorted(self._counters.items()):
            out["counters"].setdefault(name, {})[labels] = round(total, 6)
        for (name, labels), value in sorted(self._gauges.items()):
            out["gauges"].setdefault(name, {})[labels] = round(value, 6)
        for (name, labels), values in sorted(self._histograms.items()):
            out["histograms"].setdefault(name, {})[labels] = sorted(
                round(v, 6) for v in values
            )
        return out


__all__ = ["JsonCounter", "JsonGauge", "JsonHistogram", "JsonMetricsCollector"]
