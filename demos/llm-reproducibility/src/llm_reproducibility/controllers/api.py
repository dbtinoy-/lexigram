"""REST surface for the LLM reproducibility demo.

Maps the experiment runner onto HTTP so seeded, reproducible experiments
can be triggered and inspected from a browser or curl:

- ``POST /api/run``       — run a seeded experiment
- ``GET /api/runs``       — list past runs
- ``GET /api/run/{id}``   — get one run's details
- ``GET /api/health``     — readiness check

The controller returns ``Result`` values; the web pipeline renders ``Ok``
payloads and maps ``Err`` errors to ProblemDetail responses automatically.

Error-to-status mapping (declared via ``@error_status``):

    FileNotFoundError → 404
    ValueError         → 422
    Exception          → 500
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from starlette.requests import Request

from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, JSONResponse, get, post
from llm_reproducibility.config import load_lex_config
from llm_reproducibility.services.runner import run_experiment

logger = get_logger(__name__)

# RUNS_DIR points to the demo's ``runs/`` directory — one level above ``src/``.
# Each experiment creates a subdirectory: ``runs/<run_id>/``.
RUNS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "runs"


class ExperimentApiController(Controller):
    """Expose the experiment runner over HTTP.

    Lexigram pattern: controllers are stateless handlers that receive
    collaborators via constructor injection.  The framework resolves the
    controller when a request matches its routes — you never instantiate
    it manually.
    """

    def __init__(self) -> None:
        """Stateless: every handler delegates to run_experiment()."""

    @post("/api/run")
    async def run_experiment_endpoint(
        self,
        request: Request,
    ) -> Result[dict[str, Any], Exception]:
        """Run a seeded experiment and return the reproducibility digest.

        Accepts optional JSON body with ``seed`` and ``ablate`` overrides.
        Returns run_id, digest, stats, and checkpoint paths.

        Example:
            ```bash
            curl -X POST http://localhost:8095/api/run \
              -H "Content-Type: application/json" \
              -d '{"seed": 42}'
            ```
        """
        body: dict[str, Any] = {}
        try:
            raw = await request.body()
            if raw:
                body = json_loads(raw)
        except Exception:
            pass

        seed = int(body.get("seed", 42))
        ablate = body.get("ablate")

        # Load the default config — same config + same seed = identical digest.
        # This is the core reproducibility guarantee: deterministic inputs
        # produce byte-identical outputs across runs.
        config = load_lex_config()

        result = run_experiment(config, seed=seed, out_dir=RUNS_DIR, ablate=ablate)
        logger.info(
            "experiment_run_complete",
            run_id=result.run_id,
            digest=result.digest,
        )
        return Ok(
            {
                "run_id": result.run_id,
                "digest": result.digest,
                "checkpoints": len(result.checkpoint_paths),
                "traces": len(result.trace),
                "cost_dollars": result.result["totals"]["cost_dollars"],
                "totals": result.result["totals"],
            }
        )

    @get("/api/runs")
    async def list_runs(self) -> Result[list[dict[str, Any]], Exception]:
        """List all past experiment runs.

        Returns a list of run summaries sorted by directory name (newest first).
        Each summary contains ``run_id`` and ``digest`` for quick inspection.
        """
        runs: list[dict[str, Any]] = []
        if RUNS_DIR.exists():
            for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
                if not run_dir.is_dir():
                    continue
                manifest = run_dir / "reproducibility.json"
                if manifest.exists():
                    data = json_loads(manifest.read_text())
                    runs.append(
                        {
                            "run_id": data.get("run_id", run_dir.name),
                            "digest": data.get("digest", ""),
                        }
                    )
        return Ok(runs)

    @get("/api/run/{run_id}")
    async def get_run(
        self,
        run_id: str,
    ) -> Result[dict[str, Any], Exception]:
        """Return one run's details.

        Aggregates params, result, metrics, and reproducibility manifest
        into a single response for easy inspection.
        """
        run_dir = RUNS_DIR / run_id
        if not run_dir.exists():
            return Err(Exception(f"unknown run {run_id!r}"))

        result: dict[str, Any] = {}
        for name in [
            "reproducibility.json",
            "params.json",
            "result.json",
            "metrics.json",
        ]:
            path = run_dir / name
            if path.exists():
                result[name.replace(".json", "")] = json_loads(path.read_text())
        return Ok(result)

    @get("/api/health")
    async def health(self) -> JSONResponse:
        """Readiness check — always 200 if the app is up.

        Useful for load balancer health probes and monitoring.
        """
        return JSONResponse({"status": "ok", "component": "llm-reproducibility"})


__all__ = ["ExperimentApiController"]
