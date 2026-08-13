"""Seeded, config-driven LLM relay experiment harness.

Runs a fully deterministic, offline "experiment": wire Claude payloads
(drawn from a seeded PRNG) are converted through the framework's
:class:`~lexigram.ai.relay.mappers.claude.ClaudeMapper` to canonical IR
and back, while OpenTelemetry spans (:class:`AITracer`) and structured
metrics (:class:`AIMetrics`) are recorded.

Same seed + same config => byte-identical metrics, params, and
conversion results (see :func:`run_experiment` -> ``digest``).  This is
the framework's reproducibility path: no external experiment-tracking
service is required.  Runs are tracked through the evaluation subsystem
(:class:`~lexigram.ai.evaluation.LocalTracker` with seed-stable run
ids), per-iteration checkpoints land digest-verified in
:class:`~lexigram.ai.evaluation.FileCheckpointStore`, and
:class:`~lexigram.ai.evaluation.ErrorAnalysis` summarizes every run
under ``runs/<run_id>/``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import random
from typing import Any, TypeVar

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
import yaml

from lexigram.ai.evaluation.analysis import ErrorAnalysis
from lexigram.ai.evaluation.checkpoints import FileCheckpointStore
from lexigram.ai.evaluation.tracking import LocalTracker, make_run_id
from lexigram.ai.observability.metrics.core import AIMetrics
from lexigram.ai.observability.tracing.core import AITracer
from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.claude import ClaudeMapper
from lexigram.contracts.ai.experiment import (
    ExperimentConfig,
    ExperimentTrackerProtocol,
    RunStatus,
)
from lexigram.contracts.ai.relay.dto import (
    ClaudeContent,
    ClaudeResponse,
    ClaudeUsage,
)
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


@dataclass(frozen=True)
class ExperimentResult:
    """One fully reproducible experiment run."""

    run_id: str
    params: dict[str, Any]
    metrics: dict[str, Any]
    result: dict[str, Any]
    trace: list[dict[str, str | dict[str, Any]]]
    checkpoint_paths: list[str]
    analysis: dict[str, Any]
    digest: str


def _canonical(value: Any) -> str:
    """Stable, key-sorted JSON serialization for digesting."""
    return dumps_str(value, sort_keys=True)


T = TypeVar("T")


def _drive(coro_factory: Callable[[], Awaitable[T]]) -> T:
    """Run a coroutine to completion from a sync caller.

    Works both from plain scripts (no running loop, runs on this
    thread) and from notebook kernels (an event loop is already
    running: the coroutine is driven by :func:`asyncio.run` on a
    short-lived worker thread).

    Args:
        coro_factory: Factory returning the coroutine to execute.

    Returns:
        The coroutine's result.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro_factory()).result()


def _build_payload(
    rng: random.Random, index: int, ablate: str | None
) -> ClaudeResponse:
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
    checkpoint_payloads: list[tuple[str, dict[str, Any]]] = []
    summaries: list[dict[str, Any]] = []
    total_cost = 0.0

    for index in range(iterations):
        latency = round(rng.uniform(0.05, 0.30), 6)
        payload = _build_payload(rng, index, ablate)
        with tracer.trace_llm_call(provider_name, model) as span:
            converted = mapper.response_to_ir(payload, context=context)
            ir = converted.unwrap()
            roundtrip = mapper.ir_to_response(ir, context=context).unwrap()
            span.set_attribute(
                "tokens.total", ir.usage.prompt_tokens if ir.usage else 0
            )

        # Thinking blocks consume output tokens in the real API; the harness
        # accounts for them explicitly so ablation of thinking is measurable.
        thinking_tokens = sum(
            len(block.thinking or "")
            for block in payload.content
            if block.type == "thinking"
        )
        completion_tokens = (
            ir.usage.completion_tokens if ir.usage else 0
        ) + thinking_tokens
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

        checkpoint_payloads.append(
            (
                f"iteration_{index:02d}",
                {
                    "iteration": index,
                    "wire_id": payload.id,
                    "finished_text": ir.content,
                    "finish_reason": ir.finish_reason,
                    "usage": asdict(ir.usage) if ir.usage else None,
                    "thinking_tokens": thinking_tokens,
                    "cost_dollars": cost,
                    "roundtrip_stop_reason": roundtrip.stop_reason,
                    "losses": [asdict(loss) for loss in context.losses],
                },
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
        _canonical(
            {"params": params, "metrics": metrics_snapshot, "result": result}
        ).encode()
    ).hexdigest()

    variant = {**exp, "_ablate": ablate or "control"}
    run_id = make_run_id(exp["name"], seed, variant)
    run_dir = out_dir / "runs" / run_id
    checkpoint_paths, analysis = _drive(
        lambda: _persist_artifacts(
            out_dir=out_dir,
            run_id=run_id,
            exp=variant,
            seed=seed,
            ablate=ablate,
            totals=_run_totals(summaries),
            checkpoints=checkpoint_payloads,
            losses=[asdict(loss) for loss in context.losses],
        )
    )
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
        analysis=analysis,
        digest=digest,
    )


def _run_totals(summaries: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate run totals from per-iteration summaries.

    Args:
        summaries: Per-iteration summary dicts.

    Returns:
        Prompt, completion, cost, and mean-latency totals as floats.
    """
    return {
        "prompt_tokens": float(sum(s["prompt_tokens"] for s in summaries)),
        "completion_tokens": float(sum(s["completion_tokens"] for s in summaries)),
        "cost_dollars": float(sum(s["cost_dollars"] for s in summaries)),
        "latency_seconds": round(
            sum(s["latency_seconds"] for s in summaries) / max(len(summaries), 1), 6
        ),
    }


async def _persist_artifacts(
    *,
    out_dir: Path,
    run_id: str,
    exp: dict[str, Any],
    seed: int,
    ablate: str | None,
    totals: dict[str, float],
    checkpoints: list[tuple[str, dict[str, Any]]],
    losses: list[dict[str, Any]],
) -> tuple[list[str], dict[str, Any]]:
    """Persist a run through the framework experiment-tracking subsystem.

    Args:
        out_dir: Parent directory for ``runs/<run_id>/``.
        run_id: Seed-stable run identifier.
        exp: ``experiment.yaml`` experiment mapping.
        seed: PRNG seed.
        ablate: Active feature ablation; ``None`` for the full-feature run.
        totals: Aggregated run metrics persisted as the totals checkpoint.
        checkpoints: ``(slug, payload)`` pairs persisted digest-verified.
        losses: Conversion-loss records converted to error records.

    Returns:
        Checkpoint file paths and the error-analysis summary dict.
    """
    tracker: ExperimentTrackerProtocol = LocalTracker(root=out_dir)
    store = FileCheckpointStore(root=out_dir)
    run = await tracker.start(ExperimentConfig(name=exp["name"], seed=seed, config=exp))

    paths: list[str] = []
    for slug, payload in checkpoints:
        await store.save(run.run_id, slug, payload)
        paths.append(
            str(out_dir / "runs" / run.run_id / "checkpoints" / f"{slug}.json")
        )
    totals_slug = "baseline" if ablate is None else f"ablated-{ablate}"
    await store.save(run.run_id, totals_slug, totals)
    paths.append(
        str(out_dir / "runs" / run.run_id / "checkpoints" / f"{totals_slug}.json")
    )
    for name, value in totals.items():
        await tracker.log_metric(run.run_id, name, value, step=0)
    for index, loss in enumerate(losses):
        await tracker.log_error(
            run.run_id,
            str(loss.get("kind") or loss.get("type") or "conversion_loss"),
            str(loss),
            step=index,
        )

    analysis = await ErrorAnalysis(tracker).report(run.run_id)
    analysis_summary = {
        "total_records": analysis.total_records,
        "error_count": analysis.error_count,
        "error_kinds": analysis.error_kinds,
        "score_mean": analysis.score_mean,
        "score_min": analysis.score_min,
        "score_max": analysis.score_max,
        "top_errors": [asdict(e) for e in analysis.top_errors][:3],
    }
    write_json(out_dir / "runs" / run.run_id / "analysis.json", analysis_summary)
    await tracker.finish(run.run_id, status=RunStatus.COMPLETED)
    return paths, analysis_summary


def _artifact_fingerprint(config: dict[str, Any]) -> str:
    """Fingerprint the config so renamed/loaded changes never go unnoticed."""
    return hashlib.sha256(_canonical(config).encode()).hexdigest()[:12]


def write_json(path: Path, data: Any) -> Path:
    """Write JSON with deterministic key order and formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_str(data, sort_keys=True, indent=2) + "\n")
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
