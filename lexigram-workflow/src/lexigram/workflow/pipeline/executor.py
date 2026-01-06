"""In-process business process pipeline execution.

.. note::
    **Boundary with lexigram-tasks workflows:**

    This module provides synchronous in-process pipeline orchestration for
    multi-step business processes (validation → enrichment → persistence).

    For queue-backed background job chaining, use
    ``lexigram.tasks.workflows`` instead.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from lexigram import serialization as json
from lexigram.contracts.exceptions import PipelineExecutionError
from lexigram.primitives.pipeline import (
    PipelineContext,
    StepExecutionResult,
    StepStatus,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache import CacheBackendProtocol
    from lexigram.workflow.pipeline.steps import PipelineStep


def _logger() -> Any:
    from lexigram.logging import get_logger

    return get_logger(__name__)


class Pipeline:
    """Declarative pipeline for composing business workflows."""

    def __init__(
        self,
        name: str,
        steps: list[PipelineStep],
        checkpoint_store: CacheBackendProtocol | None = None,
    ) -> None:
        self.name = name
        self.steps = steps
        self._checkpoint_store = checkpoint_store
        self._validate_pipeline()

    def add_step(self, step: PipelineStep) -> None:
        """Append a step to this pipeline.

        Args:
            step: The PipelineStep to append. Validates pipeline structure
                after addition.

        Raises:
            ValueError: If the new step creates duplicate names or broken deps.
        """
        self.steps.append(step)
        self._validate_pipeline()

    def _validate_pipeline(self) -> None:
        """Validate pipeline structure and dependencies."""
        step_names = {step.name for step in self.steps}

        if len(step_names) != len(self.steps):
            duplicates = [
                name
                for name in step_names
                if sum(1 for s in self.steps if s.name == name) > 1
            ]
            msg = f"Duplicate step names found: {duplicates}"
            raise ValueError(msg)

        for step in self.steps:
            for dep in step.dependencies:
                if dep not in step_names:
                    msg = f"Step '{step.name}' depends on unknown step '{dep}'"
                    raise ValueError(msg)

        self._check_circular_dependencies()

    def _check_circular_dependencies(self) -> None:
        """Check for circular dependencies using topological sort."""
        graph = {step.name: step.dependencies for step in self.steps}

        visiting = set()
        visited = set()

        def visit(node: str) -> None:
            if node in visiting:
                msg = f"Circular dependency detected involving step '{node}'"
                raise ValueError(msg)
            if node in visited:
                return

            visiting.add(node)
            for dep in graph.get(node, []):
                visit(dep)
            visiting.remove(node)
            visited.add(node)

        for step_name in graph:
            if step_name not in visited:
                visit(step_name)

    def _get_execution_order(self) -> list[PipelineStep]:
        """Get steps in dependency order using topological sort."""
        indegree = {step.name: 0 for step in self.steps}
        adj: dict[str, list[PipelineStep]] = {step.name: [] for step in self.steps}

        for step in self.steps:
            for dep_name in step.dependencies:
                if dep_name in adj:
                    adj[dep_name].append(step)
                    indegree[step.name] += 1

        queue = [step for step in self.steps if indegree[step.name] == 0]
        result: list[PipelineStep] = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for dependent in adj.get(current.name, []):
                indegree[dependent.name] -= 1
                if indegree[dependent.name] == 0:
                    queue.append(dependent)

        if len(result) != len(self.steps):
            msg = "Pipeline has circular dependencies or unreachable steps"
            raise ValueError(msg)

        return result

    def to_dot(self) -> str:
        """Return a Graphviz DOT representation of the pipeline execution graph.

        Nodes represent pipeline steps; directed edges represent declared
        dependencies (``dep → step``).  The output can be rendered with
        ``dot -Tpng`` or pasted into an online Graphviz viewer.

        Returns:
            A string containing valid Graphviz DOT source for the pipeline.

        Example::

            dot_src = pipeline.to_dot()
            # dot -Tsvg -o pipeline.svg <<< "$(python -c '...')"
        """
        safe_name = self.name.replace('"', '\\"')
        lines: list[str] = [
            f'digraph "{safe_name}" {{',
            "    rankdir=LR;",
            '    node [shape=box, style=filled, fillcolor="#dae8fc"];',
        ]
        for step in self.steps:
            safe_step = step.name.replace('"', '\\"')
            lines.append(f'    "{safe_step}";')

        for step in self.steps:
            safe_step = step.name.replace('"', '\\"')
            for dep in step.dependencies:
                safe_dep = dep.replace('"', '\\"')
                lines.append(f'    "{safe_dep}" -> "{safe_step}";')

        lines.append("}")
        return "\n".join(lines)

    async def execute(
        self,
        initial_context: PipelineContext | None = None,
        fail_fast: bool = True,
    ) -> Result[PipelineContext, Exception]:
        """Execute the pipeline."""
        context = initial_context or PipelineContext(self.name)
        context.start_time = asyncio.get_event_loop().time()

        # Restore previously checkpointed step results when a store is available.
        checkpoint_key = f"pipeline:checkpoint:{self.name}"
        completed_step_names: set[str] = set()
        if self._checkpoint_store is not None:
            try:
                result = await self._checkpoint_store.get(checkpoint_key)
                if result.is_ok():
                    raw = result.unwrap()
                    if raw is not None:
                        payload: dict[str, Any] = json.loads(raw)
                        for step_name, result_value in payload.items():
                            context.set_step_result(step_name, result_value)
                            completed_step_names.add(step_name)
                        _logger().debug(
                            "pipeline.checkpoint_restored",
                            pipeline=self.name,
                            steps=list(completed_step_names),
                        )
            except (RuntimeError, OSError, ConnectionError, LookupError) as exc:
                _logger().warning(
                    "pipeline.checkpoint_restore_failed",
                    pipeline=self.name,
                    error=str(exc),
                )

        try:
            execution_order = self._get_execution_order()
            step_results: list[StepExecutionResult] = []

            for step in execution_order:
                # Skip steps already completed in a previous run (checkpoint resume).
                if step.name in completed_step_names:
                    step_results.append(
                        StepExecutionResult(
                            step_name=step.name,
                            status=StepStatus.SKIPPED,
                            skipped_reason="Resumed from checkpoint",
                        ),
                    )
                    continue

                skip_result = await step.should_skip(context)

                if skip_result.is_err():
                    step_results.append(
                        StepExecutionResult(
                            step_name=step.name,
                            status=StepStatus.FAILED,
                            error=skip_result.unwrap_err(),
                        ),
                    )
                    if fail_fast:
                        break
                    continue

                if skip_result.unwrap_or(False):
                    step_results.append(
                        StepExecutionResult(
                            step_name=step.name,
                            status=StepStatus.SKIPPED,
                            skipped_reason="Condition not met",
                        ),
                    )
                    continue

                start_time = asyncio.get_event_loop().time()
                step_results.append(
                    StepExecutionResult(
                        step_name=step.name,
                        status=StepStatus.RUNNING,
                    ),
                )

                try:
                    step_result: Result[Any, Exception]
                    if step.resilience is not None:
                        raw = await step.resilience.execute(step.execute, context)
                        step_result = raw if isinstance(raw, Result) else Ok(raw)
                    elif step.timeout is not None:
                        try:
                            step_value = await asyncio.wait_for(
                                step.execute(context), timeout=step.timeout
                            )
                            step_result = Ok(step_value)
                        except TimeoutError as exc:
                            step_result = Err(exc)
                    else:
                        step_result = await step.execute(context)
                    duration = asyncio.get_event_loop().time() - start_time

                    if step_result.is_ok():
                        step_value = step_result.unwrap()
                        context.set_step_result(step.name, step_value)
                        completed_step_names.add(step.name)
                        step_results[-1] = StepExecutionResult(
                            step_name=step.name,
                            status=StepStatus.COMPLETED,
                            result=step_value,
                            duration=duration,
                        )
                        # Persist checkpoint so the pipeline can resume from here
                        # on restart without re-running successful steps.
                        if self._checkpoint_store is not None:
                            try:
                                checkpoint_data = {
                                    n: context.get_step_result(n)
                                    for n in completed_step_names
                                }
                                await self._checkpoint_store.set(
                                    checkpoint_key,
                                    json.dumps(checkpoint_data, default=str),
                                )
                            except (
                                RuntimeError,
                                OSError,
                                ConnectionError,
                                LookupError,
                            ) as exc:
                                _logger().warning(
                                    "pipeline.checkpoint_save_failed",
                                    pipeline=self.name,
                                    step=step.name,
                                    error=str(exc),
                                )
                    else:
                        error_result = await step.on_error(
                            context,
                            step_result.unwrap_err(),
                        )
                        if error_result.is_ok():
                            context.set_step_result(
                                step.name,
                                error_result.unwrap(),
                            )
                            step_results[-1] = StepExecutionResult(
                                step_name=step.name,
                                status=StepStatus.COMPLETED,
                                result=error_result.unwrap(),
                                duration=duration,
                            )
                        else:
                            step_results[-1] = StepExecutionResult(
                                step_name=step.name,
                                status=StepStatus.FAILED,
                                error=step_result.unwrap_err(),
                                duration=duration,
                            )
                            if fail_fast:
                                break

                except (RuntimeError, TypeError, ValueError, OSError, LookupError) as e:
                    _logger().exception("Unexpected error in step %s", step.name)
                    duration = asyncio.get_event_loop().time() - start_time
                    step_results[-1] = StepExecutionResult(
                        step_name=step.name,
                        status=StepStatus.FAILED,
                        error=e,
                        duration=duration,
                    )
                    if fail_fast:
                        break

                raw_cleanup = await step.cleanup(context)
                cleanup_result = (
                    raw_cleanup if isinstance(raw_cleanup, Result) else Ok(raw_cleanup)
                )
                if cleanup_result.is_err():
                    _logger().error(
                        "Cleanup failed for step %s: %s",
                        step.name,
                        cleanup_result.unwrap_err(),
                    )

            context.end_time = asyncio.get_event_loop().time()
            context.add_metadata("step_results", step_results)
            context.add_metadata(
                "total_duration",
                context.end_time - context.start_time,
            )

            failed_steps = list(
                filter(lambda r: r.status == StepStatus.FAILED, step_results),
            )
            if failed_steps:
                first_failure = failed_steps[0]
                return Err(
                    PipelineExecutionError(
                        self.name,
                        first_failure.error
                        or Exception(f"Step '{first_failure.step_name}' failed"),
                    ),
                )

            # Clear checkpoint after successful completion — next run starts fresh.
            if self._checkpoint_store is not None:
                try:
                    await self._checkpoint_store.delete(checkpoint_key)
                except (RuntimeError, OSError, ConnectionError, LookupError) as exc:
                    _logger().warning(
                        "pipeline.checkpoint_clear_failed",
                        pipeline=self.name,
                        error=str(exc),
                    )

            return Ok(context)
        except (RuntimeError, TypeError, ValueError, OSError, LookupError) as e:
            _logger().exception("Unexpected error in pipeline execution")
            return Err(PipelineExecutionError(self.name, e))


__all__ = ["Pipeline"]
