"""Tool workflow node."""

from __future__ import annotations

from typing import Any

from lexigram.logging.factory import get_logger
from lexigram.workflow.graph.node import AbstractWorkflowNode, NodeType

logger = get_logger(__name__)


class ToolNode(AbstractWorkflowNode):
    """Workflow node that executes a Lexigram tool.

    Args:
        name: Node identifier.
        tool: Object implementing ToolProtocol with async execute().
        input_key: State key to read the tool primary input from.
        output_key: State key where the tool result is stored.
        extra_keys: Additional state keys forwarded to the tool as arguments.
    """

    def __init__(
        self,
        name: str,
        *,
        tool: Any,
        input_key: str = "input",
        output_key: str = "output",
        extra_keys: list[str] | None = None,
    ) -> None:
        super().__init__(name, NodeType.TOOL)
        self._tool = tool
        self._input_key = input_key
        self._output_key = output_key
        self._extra_keys = extra_keys or []

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Call the tool with state-derived arguments.

        Args:
            state: Current workflow state.

        Returns:
            Dict with {output_key: tool_result}.
        """
        args: dict[str, Any] = {"input": state.get(self._input_key, "")}
        for key in self._extra_keys:
            if key in state:
                args[key] = state[key]

        exec_fn = getattr(self._tool, "execute", None)
        if exec_fn is None:
            return {self._output_key: f"Tool {self.name!r} has no execute method"}

        try:
            raw = await exec_fn(args)
            result_text = str(getattr(raw, "result", raw) if raw is not None else "")
        except (OSError, ValueError, RuntimeError, TypeError) as exc:
            result_text = f"Tool error: {exc}"
            logger.warning("tool_node_error", node=self.name, error=str(exc))

        logger.debug("tool_node_done", node=self.name, output_len=len(result_text))
        return {self._output_key: result_text}


__all__ = ["ToolNode"]
