"""Workflow graph execution engine."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from lexigram.logging.factory import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.workflow.config import GraphConfig
from lexigram.workflow.exceptions import (
    CycleDetectedError,
    GraphExecutionError,
    GraphTimeoutError,
    GraphValidationError,
    HumanInputRequiredError,
    NodeExecutionError,
)
from lexigram.workflow.graph.state import WorkflowState
from lexigram.workflow.types import GraphResult, NodeResult

if TYPE_CHECKING:
    from lexigram.workflow.graph.edge import WorkflowEdge
    from lexigram.workflow.graph.node import AbstractWorkflowNode

logger = get_logger(__name__)


class WorkflowEngine:
    """Async directed-graph workflow executor.

    Construct via :class:`~lexigram.workflow.graph.builder.WorkflowBuilder`.

    Args:
        name: Display name for logging and checkpointing.
        nodes: Dict mapping node name to node instance.
        edges: List of all edges in the graph.
        entry_node: Name of the starting node.
        terminal_conditions: Mapping of terminal node name to optional
            condition callable (state) -> bool. If None the node is always terminal.
        config: Runtime configuration.
    """

    def __init__(
        self,
        name: str,
        nodes: dict[str, AbstractWorkflowNode],
        edges: list[WorkflowEdge],
        entry_node: str,
        terminal_conditions: dict[str, Any],
        config: GraphConfig | None = None,
        version: int = 1,
    ) -> None:
        self._name = name
        self._nodes = nodes
        self._edges = edges
        self._entry_node = entry_node
        self._terminal_conditions = terminal_conditions
        self._config = config or GraphConfig()
        self._version = version
        self._adj: dict[str, list[WorkflowEdge]] = {}
        for edge in edges:
            self._adj.setdefault(edge.source, []).append(edge)

    @property
    def name(self) -> str:
        """Workflow display name used in logs and checkpoints."""
        return self._name

    @property
    def version(self) -> int:
        """Definition schema version — incremented when the graph structure changes incompatibly."""
        return self._version

    async def execute(
        self,
        input: str,
        *,
        config: GraphConfig | None = None,
        state: dict[str, Any] | None = None,
    ) -> Result[GraphResult, GraphExecutionError]:
        """Execute the workflow from the entry node.

        Args:
            input: User input string injected as state["input"].
            config: Optional per-call config override.
            state: Optional pre-populated initial state.

        Returns:
            Ok(GraphResult) or Err(GraphExecutionError) on failure.
        """
        cfg = config or self._config
        wf_state = WorkflowState(input=input, initial=state)
        # Stamp the definition version so it can be validated on resume.
        wf_state["_definition_version"] = self._version
        node_results: list[NodeResult] = []
        start = time.monotonic()

        logger.info("workflow_start", workflow=self._name, entry=self._entry_node)

        try:
            if cfg.total_timeout > 0:
                await asyncio.wait_for(
                    self._run(cfg, wf_state, node_results),
                    timeout=cfg.total_timeout,
                )
            else:
                await self._run(cfg, wf_state, node_results)
        except TimeoutError:
            return Err(GraphTimeoutError(cfg.total_timeout))
        except HumanInputRequiredError:
            raise
        except (
            NodeExecutionError,
            CycleDetectedError,
            GraphValidationError,
        ) as exc:
            logger.warning(
                "workflow_execution_failed",
                workflow=self._name,
                error=str(exc),
            )
            raise
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            raise NodeExecutionError(
                f"Unexpected error in workflow {self._name!r}: {exc}",
                cause=exc,
            ) from exc

        elapsed = (time.monotonic() - start) * 1000
        terminal = node_results[-1].node_name if node_results else None

        logger.info(
            "workflow_complete",
            workflow=self._name,
            iterations=wf_state.iteration,
            duration_ms=round(elapsed, 2),
            terminal=terminal,
        )

        return Ok(
            GraphResult(
                final_state=wf_state.as_dict(),
                node_results=node_results,
                iterations=wf_state.iteration,
                duration_ms=elapsed,
                terminated_at=terminal,
            )
        )

    async def resume(
        self,
        checkpoint_state: dict[str, Any],
        human_response: str,
        *,
        config: GraphConfig | None = None,
    ) -> Result[GraphResult, GraphExecutionError]:
        """Resume a workflow paused at a human-in-the-loop node.

        Args:
            checkpoint_state: State dict snapshot from the checkpoint.
            human_response: Human operator input.
            config: Optional per-call config override.

        Returns:
            Ok(GraphResult) or Err(GraphExecutionError) on failure.
        """
        checkpoint_state["human_response"] = human_response
        resumed_from = checkpoint_state.get("_paused_at", self._entry_node)

        # Guard: reject resume if the definition version has changed since the
        # instance was checkpointed.  A version mismatch means the graph
        # structure may have changed, making it unsafe to continue execution
        # from the stored checkpoint.
        checkpoint_version = checkpoint_state.get("_definition_version")
        if checkpoint_version is not None and checkpoint_version != self._version:
            from lexigram.workflow.exceptions import WorkflowVersionMismatchError

            raise WorkflowVersionMismatchError(
                workflow_name=self._name,
                expected_version=int(checkpoint_version),
                actual_version=self._version,
            )

        return await self.execute(
            input=str(checkpoint_state.get("input", "")),
            config=config,
            state={**checkpoint_state, "_resumed_from": resumed_from},
        )

    async def _run(
        self,
        cfg: GraphConfig,
        state: WorkflowState,
        node_results: list[NodeResult],
    ) -> None:
        """Main traversal loop."""
        current_names: list[str] = [self._entry_node]

        while current_names:
            if state.iteration >= cfg.max_iterations:
                raise CycleDetectedError(
                    state.iteration, node=current_names[0] if current_names else None
                )

            if len(current_names) == 1:
                next_node_name = current_names[0]
                result = await self._execute_node(cfg, state, next_node_name)
                node_results.append(result)
                if result.error:
                    raise NodeExecutionError(result.error, node=next_node_name)
            else:
                results = await self._execute_parallel(cfg, state, current_names)
                node_results.extend(results)
                errors = [r for r in results if r.error]
                if errors:
                    raise NodeExecutionError(
                        errors[0].error or "parallel branch failed",
                        node=errors[0].node_name,
                    )

            last_node = node_results[-1].node_name
            if self._is_terminal(last_node, state):
                logger.info(
                    "workflow_terminal_reached",
                    workflow=self._name,
                    node=last_node,
                    iteration=state.iteration,
                )
                break

            current_names = self._next_nodes(last_node, state)

            if not current_names:
                logger.debug(
                    "workflow_implicit_terminal",
                    workflow=self._name,
                    node=last_node,
                )
                break

    async def _execute_node(
        self,
        cfg: GraphConfig,
        state: WorkflowState,
        node_name: str,
    ) -> NodeResult:
        """Execute a single node with optional timeout."""
        node = self._nodes.get(node_name)
        if node is None:
            return NodeResult(
                node_name=node_name,
                output={},
                error=f"Node {node_name!r} not found in workflow {self._name!r}",
            )

        start = time.monotonic()
        logger.debug("node_execute_start", workflow=self._name, node=node_name)

        try:
            if cfg.node_timeout > 0:
                output = await asyncio.wait_for(
                    node.execute(state.as_dict()),
                    timeout=cfg.node_timeout,
                )
            else:
                output = await node.execute(state.as_dict())

            state.merge(output)
            state.record(node_name, output)
            elapsed = (time.monotonic() - start) * 1000
            logger.debug(
                "node_execute_done",
                workflow=self._name,
                node=node_name,
                duration_ms=round(elapsed, 2),
            )
            return NodeResult(node_name=node_name, output=output, duration_ms=elapsed)

        except TimeoutError:
            elapsed = (time.monotonic() - start) * 1000
            return NodeResult(
                node_name=node_name,
                output={},
                duration_ms=elapsed,
                error=f"Node {node_name!r} timed out after {cfg.node_timeout}s",
            )
        except HumanInputRequiredError:
            state["_paused_at"] = node_name
            raise
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
            elapsed = (time.monotonic() - start) * 1000
            logger.warning(
                "node_execute_failed",
                workflow=self._name,
                node=node_name,
                error=str(exc),
            )
            return NodeResult(
                node_name=node_name,
                output={},
                duration_ms=elapsed,
                error=str(exc),
            )

    async def _execute_parallel(
        self,
        cfg: GraphConfig,
        state: WorkflowState,
        node_names: list[str],
    ) -> list[NodeResult]:
        """Execute a list of nodes concurrently via asyncio.gather."""
        max_p = cfg.max_parallel_branches
        if max_p > 0:
            node_names = node_names[:max_p]

        tasks = [self._execute_node(cfg, state, n) for n in node_names]
        results: list[NodeResult] = list(await asyncio.gather(*tasks))
        return results

    def _next_nodes(self, current_node: str, state: WorkflowState) -> list[str]:
        """Return names of nodes to visit next, respecting edge conditions."""
        edges = self._adj.get(current_node, [])
        state_dict = state.as_dict()
        active = [e for e in edges if e.is_active(state_dict)]
        if not active:
            return []
        return [e.target for e in active]

    def _is_terminal(self, node_name: str, state: WorkflowState) -> bool:
        """Return True when node_name is a terminal node for current state."""
        if node_name not in self._terminal_conditions:
            return False
        condition = self._terminal_conditions[node_name]
        if condition is None:
            return True
        try:
            return bool(condition(state.as_dict()))
        except (KeyError, TypeError, AttributeError, ValueError):
            return False

    def validate(self) -> None:
        """Validate the workflow graph structure.

        Raises:
            GraphValidationError: If the graph has structural problems.
        """
        if self._entry_node not in self._nodes:
            raise GraphValidationError(
                f"Entry node {self._entry_node!r} is not registered"
            )
        for name in self._terminal_conditions:
            if name not in self._nodes:
                raise GraphValidationError(f"Terminal node {name!r} is not registered")
        for edge in self._edges:
            if edge.source not in self._nodes:
                raise GraphValidationError(
                    f"Edge source {edge.source!r} is not a registered node"
                )
            if edge.target not in self._nodes:
                raise GraphValidationError(
                    f"Edge target {edge.target!r} is not a registered node"
                )


__all__ = ["WorkflowEngine"]
