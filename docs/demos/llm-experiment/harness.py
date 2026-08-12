"""Seeded, config-driven LLM relay experiment harness.

Runs a fully deterministic, offline "experiment": wire Claude payloads
(drawn from a seeded PRNG) are converted through the framework's
:class:`~lexigram.ai.relay.mappers.claude.ClaudeMapper` to canonical IR
and back, while OpenTelemetry spans (:class:`AITracer`) and structured
metrics (:class:`AIMetrics`) are recorded.

Same seed + same config => byte-identical metrics, params, and
conversion results (see :func:`run_experiment` -> ``digest``).  This is
the framework's reproducibility path: no external experiment-tracking
service is required; every run lands in ``runs/<run_id>/`` with
checkpoints per iteration.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from lexigram.ai.observability.metrics.core import AIMetrics
from lexigram.ai.observability.tracing.core import AITracer
from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.claude import ClaudeMapper
from lexigram.contracts.ai.relay.dto import (
    ClaudeContent,
    ClaudeRequest,
    ClaudeResponse,
    ClaudeUsage,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


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

    def observe(
        self, value: float, labels: dict[str, str] | None = None
    ) -> None:
        self._sink.histogram(self.name, value, labels)


class JsonGauge:
    """A gauge instrument that records into a deterministic JSON sink."""

    def __init__(self, name: str, sink: JsonMetricsCollector) -> None:
        self.name = name
        self._sink = sink

    def set_value(
        self, value: float, labels: dict[str, str] | None = None
    ) -> None:
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
        return json.dumps(labels, sort_keys=True, separators=(",", ":"))

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


@dataclass(frozen=True)
class ExperimentResult:
    """One fully reproducible experiment run."""

    run_id: str
    params: dict[str, Any]
    metrics: dict[str, Any]
    result: dict[str, Any]
    trace: list[dict[str, str | dict[str, Any]]]
    checkpoint_paths: list[str]
    digest: str


def _canonical(value: Any) -> str:
    """Stable, key-sorted JSON serialization for digesting."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _build_payload(rng: random.Random, index: int, ablate: str | None) -> ClaudeResponse:
    """Build a deterministic wire Claude response payload.

    Args:
        rng: The seeded PRNG that drives all synthetic values.
        index: Iteration index (stable across runs).
        ablate: Feature to drop ("thinking") or ``None``.

    Returns:
        A Claude response payload with seeded text, thinking, and usage.
    """
    blocks = [ClaudeContent(type="text", text=f"seeded reply {index}")]
    if ablate != "thinking":
        blocks.append(
            ClaudeContent(
                type="thinking",
                thinking=f"thought {index}",
                signature=f"sig-{index}",
            )
        )
    return ClaudeResponse(
        id=f"resp-{index}",
        model="claude-3-5-sonnet",
        content=blocks,
        stop_reason="end_turn",
        usage=ClaudeUsage(
            input_tokens=rng.randint(8, 40),
            output_tokens=rng.randint(16, 96),
            cache_read_input_tokens=rng.randint(0, 12),
            cache_creation_input_tokens=rng.randint(0, 6),
        ),
    )


def run_experiment(
    config: dict[str, Any],
    *,
    seed: int,
    out_dir: Path,
    ablate: str | None = None,
) -> ExperimentResult:
    """Run the seeded experiment and persist all artifacts.

    Args:
        config: Parsed ``experiment.yaml`` mapping.
        seed: PRNG seed; same seed reproduces the run exactly.
        out_dir: Parent directory for ``runs/<run_id>/``.
        ablate: Optional feature ablation ("thinking") or ``None``.

    Returns:
        The structured, digest-pinned :class:`ExperimentResult`.

    Example:
        ```python
        result = run_experiment(config, seed=42, out_dir=Path("runs"))
        assert result.digest == run_experiment(config, seed=42, out_dir=Path("runs")).digest
        ```
    """
    exp = config["experiment"]
    rng = random.Random(seed)
    mapper = ClaudeMapper()
    context = ConversionContext()

    collector = JsonMetricsCollector()
    metrics = AIMetrics(collector=collector)

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = AITracer(tracer=provider.get_tracer("lexigram-experiment"))

    model = exp["model"]
    provider_name = exp["provider"]
    iterations = int(exp["iterations"])
    labels = {"provider": provider_name, "model": model}
    checkpoint_paths: list[str] = []
    summaries: list[dict[str, Any]] = []
    total_cost = 0.0

    for index in range(iterations):
        latency = round(rng.uniform(0.05, 0.30), 6)
        payload = _build_payload(rng, index, ablate)
        with tracer.trace_llm_call(provider_name, model) as span:
            converted = mapper.response_to_ir(payload, context=context)
            ir = converted.unwrap()
            roundtrip = mapper.ir_to_response(ir, context=context).unwrap()
            span.set_attribute("tokens.total", ir.usage.prompt_tokens if ir.usage else 0)

        # Thinking blocks consume output tokens in the real API; the harness
        # accounts for them explicitly so ablation of thinking is measurable.
        thinking_tokens = sum(
            len(block.thinking or "")
            for block in payload.content
            if block.type == "thinking"
        )
        completion_tokens = (ir.usage.completion_tokens if ir.usage else 0) + thinking_tokens
        token_total = (ir.usage.prompt_tokens if ir.usage else 0) + completion_tokens
        cost = round(
            (ir.usage.prompt_tokens * 3.0 + completion_tokens * 15.0) / 1_000_000, 6
        )
        total_cost += cost
        metrics.llm_requests_total.increment(labels={**labels, "status": "success"})
        metrics.llm_tokens_total.increment(amount=token_total, labels=labels)
        metrics.llm_duration_seconds.observe(value=latency, labels=labels)
        metrics.llm_cost_dollars.increment(amount=cost, labels=labels)
        if roundtrip.stop_reason:
            metrics.llm_requests_total.increment(
                labels={**labels, "stop": roundtrip.stop_reason}
            )

        checkpoint_paths.append(
            str(
                write_json(
                    out_dir / f"checkpoints" / f"iteration_{index:02d}.json",
                    {
                        "iteration": index,
                        "wire_id": payload.id,
                        "finished_text": ir.content,
                        "finish_reason": ir.finish_reason,
                        "usage": asdict(ir.usage) if ir.usage else None,
                        "thinking_tokens": thinking_tokens,
                        "cost_dollars": cost,
                        "roundtrip_stop_reason": roundtrip.stop_reason,
                        "losses": [asdict(l) for l in context.losses],
                    },
                )
            )
        )
        summaries.append(
            {
                "iteration": index,
                "text": ir.content,
                "finish_reason": ir.finish_reason,
                "prompt_tokens": ir.usage.prompt_tokens if ir.usage else 0,
                "completion_tokens": completion_tokens,
                "latency_seconds": latency,
                "cost_dollars": cost,
            }
        )

    params = {
        "experiment": exp,
        "seed": seed,
        "ablation": ablate,
        "artifact_hash": _artifact_fingerprint(config),
    }
    result = {
        "iterations": summaries,
        "totals": {
            "requests": iterations,
            "prompt_tokens": sum(s["prompt_tokens"] for s in summaries),
            "completion_tokens": sum(s["completion_tokens"] for s in summaries),
            "cost_dollars": round(total_cost, 6),
            "losses": len(context.losses),
        },
    }
    metrics_snapshot = collector.snapshot()
    trace = [
        {"name": span.name, "attributes": dict(span.attributes or {})}
        for span in sorted(exporter.get_finished_spans(), key=lambda s: s.name or "")
    ]
    digest = hashlib.sha256(
        _canonical({"params": params, "metrics": metrics_snapshot, "result": result}).encode()
    ).hexdigest()

    run_id = f"{exp['name']}-{seed}-{digest[:8]}"
    run_dir = out_dir / run_id
    write_json(run_dir / "params.json", params)
    write_json(run_dir / "metrics.json", metrics_snapshot)
    write_json(run_dir / "result.json", result)
    write_json(run_dir / "trace.json", {"spans": trace})
    write_json(run_dir / "reproducibility.json", {"run_id": run_id, "digest": digest})

    exporter.shutdown()
    provider.shutdown()
    return ExperimentResult(
        run_id=run_id,
        params=params,
        metrics=metrics_snapshot,
        result=result,
        trace=trace,
        checkpoint_paths=checkpoint_paths,
        digest=digest,
    )


def _artifact_fingerprint(config: dict[str, Any]) -> str:
    """Fingerprint the config so renamed/loaded changes never go unnoticed."""
    return hashlib.sha256(_canonical(config).encode()).hexdigest()[:12]


def write_json(path: Path, data: Any) -> Path:
    """Write JSON with deterministic key order and formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return path


def load_config(path: Path) -> dict[str, Any]:
    """Load an experiment YAML config."""
    return yaml.safe_load(path.read_text())


def metrics_delta(run_a: ExperimentResult, run_b: ExperimentResult) -> dict[str, Any]:
    """Return the metrics delta between two runs for ablation analysis.

    Args:
        run_a: Baseline run (e.g. full feature set).
        run_b: Ablated run (e.g. thinking blocks dropped).

    Returns:
        Per-metric counter deltas and histogram observation count deltas.
    """
    deltas: dict[str, Any] = {}
    for name, series in run_a.metrics["counters"].items():
        baseline = sum(series.values())
        other = run_b.metrics["counters"].get(name, {})
        deltas[name] = round(sum(other.values()) - baseline, 6)
    for name, series in run_a.metrics["histograms"].items():
        baseline = sum(len(v) for v in series.values())
        other = run_b.metrics["histograms"].get(name, {})
        deltas[name] = sum(len(v) for v in other.values()) - baseline
    return deltas