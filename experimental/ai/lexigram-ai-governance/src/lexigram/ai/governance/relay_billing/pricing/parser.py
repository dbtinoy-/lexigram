"""Restricted price-expression parser and evaluator.

Price expressions are ported from the relaykit billing conventions and
evaluated by a small allow-listed parser: numeric literals, named usage
dimensions, ``+ - * /``, ``min``, ``max``, and parentheses.  Attribute
access, arbitrary calls, exponentiation, assignment, imports, and
unbounded recursion are rejected.  Every safety violation is surfaced as
a :class:`~lexigram.contracts.ai.governance.RelayBillingError` instead of
clamping silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, DecimalException, InvalidOperation
import re

from lexigram.contracts.ai.governance import RelayBillingError, invalid_usage
from lexigram.contracts.ai.relay import RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = [
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_SCALE",
    "MAX_EXPRESSION_LENGTH",
    "MAX_PARSE_DEPTH",
    "evaluate_expression",
]

_NUMBER_RE = re.compile(r"\d+(\.\d+)?([eE][+-]?\d+)?")
_NAME_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

MAX_EXPRESSION_LENGTH = 512
MAX_PARSE_DEPTH = 64
DEFAULT_SCALE = 10
DEFAULT_MAX_TOKENS = 2**31 - 1

_ALLOWED_DIMENSION_NAMES = (
    "prompt_tokens",
    "completion_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "reasoning_tokens",
    "audio_input_tokens",
    "audio_output_tokens",
    "image_tokens",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)


class _ExpressionError(Exception):
    """Internal control flow for expression parsing and evaluation."""


@dataclass(frozen=True, slots=True)
class _Token:
    """One lexical token of a price expression."""

    kind: str
    value: str = ""


@dataclass(frozen=True, slots=True)
class _NumberNode:
    """Literal numeric node."""

    value: Decimal


@dataclass(frozen=True, slots=True)
class _DimensionNode:
    """Named usage dimension node."""

    name: str


@dataclass(frozen=True, slots=True)
class _BinaryNode:
    """Binary arithmetic node (``+ - * /``)."""

    operator: str
    left: _Node
    right: _Node


@dataclass(frozen=True, slots=True)
class _ExtremeNode:
    """``min``/``max`` call node."""

    operator: str
    left: _Node
    right: _Node


_Node = _NumberNode | _DimensionNode | _BinaryNode | _ExtremeNode


def _syntax_error(expression: str) -> RelayBillingError | None:
    """Return the parse error for *expression*, or ``None`` if valid."""
    result = _tokenize(expression)
    if result.is_err():
        return result.unwrap_err()
    parsed = _parse(result.unwrap())
    if parsed.is_err():
        return parsed.unwrap_err()
    return None


def _tokenize(expression: str) -> Result[list[_Token], RelayBillingError]:
    """Tokenize a price expression, rejecting unsupported characters."""
    if len(expression) > MAX_EXPRESSION_LENGTH:
        return Err(
            invalid_usage(
                message=f"price expression exceeds {MAX_EXPRESSION_LENGTH} chars"
            )
        )
    tokens: list[_Token] = []
    index = 0
    length = len(expression)
    while index < length:
        char = expression[index]
        if char.isspace():
            index += 1
            continue
        if char.isdigit():
            match = _NUMBER_RE.match(expression, index)
            assert match is not None  # noqa: S101  # regex pre-guaranteed by isdigit() branch
            tokens.append(_Token(kind="NUMBER", value=match.group(0)))
            index = match.end()
            continue
        if char.isalpha() or char == "_":
            match = _NAME_RE.match(expression, index)
            assert match is not None  # noqa: S101  # regex pre-guaranteed by isalpha() branch
            tokens.append(_Token(kind="NAME", value=match.group(0)))
            index = match.end()
            continue
        if char in "+-*/":
            tokens.append(_Token(kind="OP", value=char))
            index += 1
            continue
        if char == "(":
            tokens.append(_Token(kind="LPAREN"))
            index += 1
            continue
        if char == ")":
            tokens.append(_Token(kind="RPAREN"))
            index += 1
            continue
        if char == ",":
            tokens.append(_Token(kind="COMMA"))
            index += 1
            continue
        return Err(
            invalid_usage(message=f"unsupported character {char!r} in price expression")
        )
    return Ok(tokens)


def _parse(tokens: list[_Token]) -> Result[_Node, RelayBillingError]:
    """Parse tokens into an allow-listed AST."""

    position = 0

    def peek() -> _Token | None:
        """Return the next unconsumed token, if any."""
        if position < len(tokens):
            return tokens[position]
        return None

    def advance() -> _Token:
        """Consume and return the next token."""
        nonlocal position
        token = tokens[position]
        position += 1
        return token

    def expect(kind: str) -> _Token:
        """Consume a token of *kind* or raise a parse error."""
        token = peek()
        if token is None or token.kind != kind:
            raise _ExpressionError(f"expected {kind}")
        return advance()

    def parse_expression(depth: int) -> _Node:
        """Parse ``+ -``; depth bounds recursion."""
        if depth > MAX_PARSE_DEPTH:
            raise _ExpressionError("expression nested too deeply")
        node = parse_term(depth + 1)
        while True:
            token = peek()
            if token is not None and token.kind == "OP" and token.value in "+-":
                advance()
                node = _BinaryNode(
                    operator=token.value,
                    left=node,
                    right=parse_term(depth + 1),
                )
            else:
                return node

    def parse_term(depth: int) -> _Node:
        """Parse ``* /``; depth bounds recursion."""
        node = parse_factor(depth + 1)
        while True:
            token = peek()
            if token is not None and token.kind == "OP" and token.value in "*/":
                advance()
                node = _BinaryNode(
                    operator=token.value,
                    left=node,
                    right=parse_factor(depth + 1),
                )
            else:
                return node

    def parse_factor(depth: int) -> _Node:
        """Parse literals, dimensions, parentheses, and min/max calls."""
        if depth > MAX_PARSE_DEPTH:
            raise _ExpressionError("expression nested too deeply")
        token = peek()
        if token is None:
            raise _ExpressionError("unexpected end of expression")
        if token.kind == "NUMBER":
            advance()
            try:
                return _NumberNode(value=Decimal(token.value))
            except InvalidOperation as exc:
                raise _ExpressionError("invalid numeric literal") from exc
        if token.kind == "NAME":
            advance()
            if token.value in ("min", "max"):
                expect("LPAREN")
                left = parse_expression(depth + 1)
                expect("COMMA")
                right = parse_expression(depth + 1)
                expect("RPAREN")
                return _ExtremeNode(operator=token.value, left=left, right=right)
            following = peek()
            if following is not None and following.kind == "LPAREN":
                raise _ExpressionError(f"call {token.value!r} not allowed")
            return _DimensionNode(name=token.value)
        if token.kind == "LPAREN":
            advance()
            node = parse_expression(depth + 1)
            expect("RPAREN")
            return node
        raise _ExpressionError(f"unexpected token {token.value or token.kind!r}")

    if not tokens:
        return Err(invalid_usage(message="empty price expression"))
    try:
        node = parse_expression(0)
        if position != len(tokens):
            token = tokens[position]
            raise _ExpressionError(
                f"unexpected trailing token {token.value or token.kind!r}"
            )
        return Ok(node)
    except _ExpressionError as exc:
        return Err(invalid_usage(message=str(exc)))


def _evaluate(node: _Node, usage: RelayUsage, max_tokens: int) -> Decimal:
    """Evaluate an AST against usage, raising on any safety violation."""
    if isinstance(node, _NumberNode):
        return node.value
    if isinstance(node, _DimensionNode):
        if node.name not in _ALLOWED_DIMENSION_NAMES:
            raise _ExpressionError(f"unknown usage dimension {node.name!r}")
        value = getattr(usage, node.name)
        if value < 0:
            raise _ExpressionError(f"negative usage dimension {node.name}")
        if value > max_tokens:
            raise _ExpressionError(f"usage dimension {node.name} exceeds maximum")
        return Decimal(value)
    left = _evaluate(node.left, usage, max_tokens)
    right = _evaluate(node.right, usage, max_tokens)
    try:
        if isinstance(node, _BinaryNode):
            if node.operator == "+":
                result = left + right
            elif node.operator == "-":
                result = left - right
            elif node.operator == "*":
                result = left * right
            else:
                if right == 0:
                    raise _ExpressionError("division by zero")
                result = left / right
        else:
            result = min(left, right) if node.operator == "min" else max(left, right)
    except DecimalException as exc:
        raise _ExpressionError("decimal arithmetic failure") from exc
    if not result.is_finite():
        raise _ExpressionError("non-finite result")
    if result < 0:
        raise _ExpressionError("negative result")
    return result


def evaluate_expression(
    expression: str,
    usage: RelayUsage,
    *,
    scale: int = DEFAULT_SCALE,
    rounding: str = ROUND_HALF_UP,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> Result[Decimal, RelayBillingError]:
    """Evaluate a price expression against normalized usage.

    Args:
        expression: Price expression over named usage dimensions.
        usage: Normalized usage the expression is evaluated against.
        scale: Decimal places retained on the result.
        rounding: Rounding mode applied to the result.
        max_tokens: Integer maximum for any usage dimension.

    Returns:
        Ok(rounded charge) on success, Err(RelayBillingError) on any
        syntax or arithmetic safety violation.
    """
    if scale < 0:
        return Err(invalid_usage(message="scale must be non-negative"))
    tokens = _tokenize(expression)
    if tokens.is_err():
        return Err(tokens.unwrap_err())
    parsed = _parse(tokens.unwrap())
    if parsed.is_err():
        return Err(parsed.unwrap_err())
    try:
        value = _evaluate(parsed.unwrap(), usage, max_tokens)
    except _ExpressionError as exc:
        return Err(invalid_usage(message=str(exc)))
    try:
        quantum = Decimal(1).scaleb(-scale)
        return Ok(value.quantize(quantum, rounding=rounding))
    except DecimalException:
        return Err(invalid_usage(message="charge rounding failed"))
