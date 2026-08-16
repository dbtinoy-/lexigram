"""Workflow runner — wraps WorkflowEngine with optional retry logic."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from lexigram.logging.factory import get_logger
from lexigram.result import Err, Result
from lexigram.workflow.graph.state import WorkflowState

if TYPE_CHECKING:
    from lexigram.workflow.exceptions import GraphExecutionError
    from lexigram.workflow.graph.engine import WorkflowEngine
    from lexigram.workflow.types import GraphResult

logger = get_logger(__name__)


class WorkflowRunner:
    """Execute a WorkflowEngine with retry and optional checkpointing.

    Args:
        engine: The WorkflowEngine to run.
        max_retries: Maximum attempts after the first failure.
        retry_delay: Seconds to wait between attempts.
        checkpoint: Optional WorkflowCheckpoint instance.
    """

    def __init__(
        self,
        engine: WorkflowEngine,
        *,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        checkpoint: Any | None = None,
    ) -> None:
        self._engine = engine
        self._max_retries = max(0, max_retries)
        self._retry_delay = max(0.0, retry_delay)
        self._checkpoint = checkpoint

    async def run(
        self,
        input: str,
        *,
        state: dict[str, Any] | WorkflowState | None = None,
    ) -> Result[GraphResult, GraphExecutionError]:
        """Execute the workflow, retrying on transient failures.

        Args:
            input: Workflow input string.
            state: Optional pre-populated WorkflowState.

        Returns:
            Ok(GraphResult) on success or Err(GraphExecutionError) on
            permanent failure.

        Raises:
            HumanInputRequiredError: When a HumanNode pauses execution.
        """
        attempts = 0
        last_error: GraphExecutionError | None = None

        while attempts <= self._max_retries:
            if attempts > 0:
                logger.info(
                    "workflow_runner_retry",
                    engine=self._engine.name,
                    attempt=attempts + 1,
                )
                await asyncio.sleep(self._retry_delay)

            initial_state = (
                state.as_dict() if isinstance(state, WorkflowState) else state
            )
            result = await self._engine.execute(input, state=initial_state)

            attempts += 1

            if result.is_ok():
                logger.debug(
                    "workflow_runner_success",
                    engine=self._engine.name,
                    attempts=attempts,
                )
                return result

            last_error = result.unwrap_err()
            logger.warning(
                "workflow_runner_attempt_failed",
                engine=self._engine.name,
                attempt=attempts,
                error=str(last_error),
            )

        logger.error(
            "workflow_runner_exhausted",
            engine=self._engine.name,
            attempts=attempts,
        )
        assert last_error is not None  # noqa: S101  # exhaustion path always records an error
        return Err(last_error)

    async def resume(
        self,
        human_response: str,
        *,
        state: WorkflowState,
        response_key: str = "human_response",
    ) -> Result[GraphResult, GraphExecutionError]:
        """Resume a paused HITL workflow by injecting the human response.

        Args:
            human_response: The operator response to inject into state.
            state: The WorkflowState from the paused point.
            response_key: Key under which to store human_response.

        Returns:
            Ok(GraphResult) on success or Err(GraphExecutionError).
        """
        state.merge({response_key: human_response})
        return await self.run(state.get("input", ""), state=state)


__all__ = ["WorkflowRunner"]
