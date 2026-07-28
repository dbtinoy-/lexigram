"""Subworkflow node — embeds a nested WorkflowEngine."""

from __future__ import annotations

from typing import Any

from lexigram.logging.factory import get_logger
from lexigram.workflow.graph.node import AbstractWorkflowNode, NodeType

logger = get_logger(__name__)


class SubworkflowNode(AbstractWorkflowNode):
    """Embed a nested WorkflowEngine as a single node in a parent workflow.

    Args:
        name: Node identifier.
        workflow: A WorkflowEngine instance to nest.
        input_key: State key to read as the subworkflow input value.
        output_key: State key where the subworkflow result is stored.
    """

    def __init__(
        self,
        name: str,
        *,
        workflow: Any,
        input_key: str = "input",
        output_key: str = "output",
    ) -> None:
        super().__init__(name, NodeType.SUBWORKFLOW)
        self._workflow = workflow
        self._input_key = input_key
        self._output_key = output_key

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the nested workflow with the current parent state.

        Args:
            state: Current parent workflow state.

        Returns:
            Dict with {output_key: subworkflow_output} on success
            or {output_key: "Subworkflow error: ..."} on failure.
        """
        sub_input = state.get(self._input_key, "")
        logger.debug("subworkflow_node_start", node=self.name)
        try:
            result = await self._workflow.execute(sub_input, state=state)
        except (RuntimeError, ValueError, OSError) as exc:
            error_text = f"Subworkflow error: {exc}"
            logger.warning("subworkflow_node_error", node=self.name, error=str(exc))
            return {self._output_key: error_text}

        if result.is_err():
            error_text = f"Subworkflow error: {result.unwrap_err()}"
            logger.warning("subworkflow_node_err", node=self.name, error=error_text)
            return {self._output_key: error_text}

        sub_result = result.unwrap()
        output = sub_result.output
        logger.debug("subworkflow_node_done", node=self.name)
        return {self._output_key: output}


__all__ = ["SubworkflowNode"]
