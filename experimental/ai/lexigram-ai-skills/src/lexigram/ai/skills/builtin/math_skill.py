"""MathSkill — safe arithmetic expression evaluator using AST."""

from __future__ import annotations

import ast
import operator
from typing import Any

from lexigram.ai.skills.base import AbstractSkill
from lexigram.ai.skills.exceptions import SkillExecutionError
from lexigram.contracts.ai.skills import SkillDefinition, SkillError, SkillResult
from lexigram.result import Err, Ok, Result

# Only these AST node types are allowed in expressions.
_ALLOWED_NODES = {
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
}

_BINOPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARYOPS: dict[type[ast.unaryop], Any] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _check_nodes(node: ast.AST) -> None:
    """Raise ValueError for any AST node not in the safe-list.

    Args:
        node: Root AST node to validate.

    Raises:
        ValueError: When an unsafe node type is encountered.
    """
    for child in ast.walk(node):
        if type(child) not in _ALLOWED_NODES:
            raise ValueError(f"Unsafe expression node: {type(child).__name__}")


def _eval_node(node: ast.AST) -> float:
    """Recursively evaluate a safe AST expression.

    Args:
        node: An AST node to evaluate.

    Returns:
        The numeric result.

    Raises:
        ValueError: If the node type is unsupported.
    """
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise TypeError(f"Non-numeric constant: {node.value!r}")
        return float(node.value)
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op_fn = _BINOPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported binary op: {type(node.op).__name__}")
        return op_fn(left, right)
    if isinstance(node, ast.UnaryOp):
        op_fn = _UNARYOPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported unary op: {type(node.op).__name__}")
        return op_fn(_eval_node(node.operand))
    raise ValueError(f"Unsupported node: {type(node).__name__}")


def safe_eval(expression: str) -> float:
    """Evaluate *expression* using only arithmetic AST nodes.

    Args:
        expression: A mathematical expression string, e.g. ``"2 ** 10 + 3 * 4"``.

    Returns:
        The computed float result.

    Raises:
        ValueError: If the expression contains unsafe constructs.
        SyntaxError: If the expression is syntactically invalid.
    """
    tree = ast.parse(expression.strip(), mode="eval")
    _check_nodes(tree)
    return _eval_node(tree)


class MathSkill(AbstractSkill):
    """Evaluate safe arithmetic expressions.

    Supports the operators ``+``, ``-``, ``*``, ``/``, ``//``, ``%``, and
    ``**``.  No functions, names, or string literals are permitted.

    Example output::

        {"result": 1024.0, "expression": "2 ** 10"}
    """

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition.

        Returns:
            SkillDefinition for the math_calculate skill.
        """
        return SkillDefinition(
            name="math_calculate",
            description=(
                "Evaluate a safe arithmetic expression. "
                "Supports +, -, *, /, //, %, ** operators."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Arithmetic expression to evaluate.",
                    },
                },
                "required": ["expression"],
            },
            category="utility",
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Evaluate the expression and return the result.

        Args:
            **kwargs: Requires ``expression`` (str).

        Returns:
            Ok result with ``result`` and ``expression`` keys, or Err on
            invalid expression.
        """
        expression: str = kwargs.get("expression", "")
        try:
            value = safe_eval(expression)
        except (ValueError, SyntaxError, ZeroDivisionError) as exc:
            return Err(
                SkillExecutionError(
                    f"Invalid expression '{expression}': {exc}", cause=exc
                )
            )
        return Ok(
            SkillResult(
                skill_name="math_calculate",
                success=True,
                output={"result": value, "expression": expression},
            )
        )
