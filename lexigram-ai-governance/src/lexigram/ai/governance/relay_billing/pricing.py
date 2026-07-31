"""Decimal price calculation and restricted expression evaluation.

Computes per-dimension relay charges from normalized ``RelayUsage`` and
configured price snapshots.  Price expressions are ported from the
relaykit billing conventions and evaluated by a small allow-listed
parser: numeric literals, named usage dimensions, ``+ - * /``, ``min``,
``max``, and parentheses.  Attribute access, arbitrary calls,
exponentiation, assignment, imports, and unbounded recursion are
rejected.  All arithmetic uses non-negative ``Decimal`` with explicit
per-dimension rounding; every safety violation returns a
``RelayBillingError`` instead of clamping silently.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import (
    ROUND_HALF_UP,
    Decimal,
    DecimalException,
    InvalidOperation,
)
import re

from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayChargeBreakdown,
    RelayPriceEstimatorProtocol,
    charge_overflow,
    invalid_usage,
    unknown_price,
)
from lexigram.contracts.ai.llm import CostEstimatorProtocol
from lexigram.contracts.ai.relay import RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = [
    "BREAKDOWN_FIELDS",
    "DEFAULT_MAX_CHARGE",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_SCALE",
    "PriceSnapshot",
    "RelayPricingEngine",
    "SimpleCostEstimator",
    "evaluate_expression",
]

BREAKDOWN_FIELDS = (
    "prompt",
    "cached_prompt",
    "completion",
    "reasoning",
    "audio_input",
    "audio_output",
    "image",
)

_DIMENSION_TO_USAGE = {
    "prompt": "prompt_tokens",
    "cached_prompt": "cache_read_tokens",
    "completion": "completion_tokens",
    "reasoning": "reasoning_tokens",
    "audio_input": "audio_input_tokens",
    "audio_output": "audio_output_tokens",
    "image": "image_tokens",
}

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

_NUMBER_RE = re.compile(r"\d+(\.\d+)?([eE][+-]?\d+)?")
_NAME_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

MAX_EXPRESSION_LENGTH = 512
MAX_PARSE_DEPTH = 64
DEFAULT_SCALE = 10
DEFAULT_MAX_CHARGE = Decimal("1_000_000")
DEFAULT_MAX_TOKENS = 2**31 - 1
_PER_1M = Decimal(1_000_000)


class _ExpressionError(Exception):
    """Internal control flow for expression parsing and evaluation."""


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    """Configured per-dimension price expressions for one model.

    Each expression is evaluated against the named usage dimensions of
    ``RelayUsage``, e.g. ``"prompt_tokens * 0.0000025"``.  A dimension
    without an expression contributes zero while remaining present in
    the audit breakdown.

    Attributes:
        expressions: Mapping of breakdown field name to expression string.
    """

    expressions: Mapping[str, str]

    def __post_init__(self) -> None:
        """Validate dimension names and expression syntax."""
        unknown = set(self.expressions) - set(BREAKDOWN_FIELDS)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown price dimensions: {names}")
        for field_name, expression in self.expressions.items():
            if not expression.strip():
                raise ValueError(f"empty expression for dimension {field_name}")
            if _syntax_error(expression) is not None:
                raise ValueError(
                    f"invalid expression for dimension {field_name}: {expression}"
                )

    @classmethod
    def from_per_1m(cls, prices: Mapping[str, Decimal]) -> PriceSnapshot:
        """Build a snapshot from per-1M-token Decimal prices.

        Args:
            prices: Per-1M-token price per breakdown dimension; missing
                dimensions default to zero.

        Returns:
            A snapshot whose expressions multiply each usage dimension
            by its per-token price.

        Raises:
            ValueError: If a price is negative or a dimension is unknown.
        """
        unknown = set(prices) - set(BREAKDOWN_FIELDS)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown price dimensions: {names}")
        expressions: dict[str, str] = {}
        for field_name in BREAKDOWN_FIELDS:
            price = prices.get(field_name, Decimal(0))
            if price < 0:
                raise ValueError(f"negative price for dimension {field_name}")
            if price == 0:
                expressions[field_name] = "0"
                continue
            usage_field = _DIMENSION_TO_USAGE[field_name]
            per_token = (price / _PER_1M).normalize()
            expressions[field_name] = f"{usage_field} * {format(per_token, 'f')}"
        return cls(expressions=expressions)


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


class RelayPricingEngine(RelayPriceEstimatorProtocol):
    """Detailed per-dimension relay price estimator.

    Args:
        price_provider: Callable returning the ``PriceSnapshot`` for a
            ``(model, provider, channel)`` triple, or ``None`` when the
            model has no configured price.
        scale: Default decimal places retained per dimension.
        rounding: Default rounding mode applied per dimension.
        max_charge: Maximum total charge; above it fails closed.
        max_tokens: Integer maximum for any usage dimension.
        dimension_scales: Per-dimension decimal places overrides.
        dimension_roundings: Per-dimension rounding mode overrides.

    Raises:
        ValueError: If *max_charge* or *scale* is negative, or a
            dimension override references an unknown breakdown field.
    """

    def __init__(
        self,
        price_provider: Callable[[str, str, str], PriceSnapshot | None],
        *,
        scale: int = DEFAULT_SCALE,
        rounding: str = ROUND_HALF_UP,
        max_charge: Decimal = DEFAULT_MAX_CHARGE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        dimension_scales: Mapping[str, int] | None = None,
        dimension_roundings: Mapping[str, str] | None = None,
    ) -> None:
        if scale < 0:
            raise ValueError("scale must be non-negative")
        if max_charge < 0:
            raise ValueError("max_charge must be non-negative")
        unknown_scales = set(dimension_scales or {}) - set(BREAKDOWN_FIELDS)
        if unknown_scales:
            names = ", ".join(sorted(unknown_scales))
            raise ValueError(f"unknown dimension scales: {names}")
        unknown_roundings = set(dimension_roundings or {}) - set(BREAKDOWN_FIELDS)
        if unknown_roundings:
            names = ", ".join(sorted(unknown_roundings))
            raise ValueError(f"unknown dimension roundings: {names}")
        self._price_provider = price_provider
        self._scale = scale
        self._rounding = rounding
        self._max_charge = max_charge
        self._max_tokens = max_tokens
        self._dimension_scales = dict(dimension_scales or {})
        self._dimension_roundings = dict(dimension_roundings or {})

    def estimate_charge(
        self,
        model: str,
        usage: RelayUsage,
        *,
        provider: str = "",
        channel: str = "",
    ) -> Result[RelayChargeBreakdown, RelayBillingError]:
        """Compute the per-dimension charge breakdown for *usage*.

        Returns:
            Ok(breakdown) on success, Err(RelayBillingError) on unknown
            prices, negative usage, overflow, or expression failures.
        """
        for name in _ALLOWED_DIMENSION_NAMES:
            if getattr(usage, name) < 0:
                return Err(invalid_usage(message=f"negative usage dimension {name}"))
        snapshot = self._price_provider(model, provider, channel)
        if snapshot is None:
            return Err(
                unknown_price(message=f"no price configured for model {model!r}")
            )
        charges: dict[str, Decimal] = {}
        for field_name in BREAKDOWN_FIELDS:
            expression = snapshot.expressions.get(field_name, "0")
            scale = self._dimension_scales.get(field_name, self._scale)
            rounding = self._dimension_roundings.get(field_name, self._rounding)
            charge = evaluate_expression(
                expression,
                usage,
                scale=scale,
                rounding=rounding,
                max_tokens=self._max_tokens,
            )
            if charge.is_err():
                return Err(charge.unwrap_err())
            charges[field_name] = charge.unwrap()
        total = sum(charges.values(), Decimal(0))
        if total > self._max_charge:
            return Err(
                charge_overflow(
                    message=f"charge {total} exceeds configured maximum {self._max_charge}"
                )
            )
        return Ok(RelayChargeBreakdown(**charges, total=total))


class SimpleCostEstimator(RelayPriceEstimatorProtocol):
    """Simple prompt/completion price estimator over ``CostEstimatorProtocol``.

    Priced at the underlying estimator's input and output rates; the
    detailed relay dimensions are always zero.  Unknown models yield a
    zero charge, matching the estimator's unknown-model-zero policy.

    Args:
        estimator: Existing LLM cost estimator reused for the simple path.
        scale: Decimal places retained on each part of the charge.
        rounding: Rounding mode applied to each part of the charge.
        max_charge: Maximum total charge; above it fails closed.
    """

    def __init__(
        self,
        estimator: CostEstimatorProtocol,
        *,
        scale: int = DEFAULT_SCALE,
        rounding: str = ROUND_HALF_UP,
        max_charge: Decimal = DEFAULT_MAX_CHARGE,
    ) -> None:
        if scale < 0:
            raise ValueError("scale must be non-negative")
        if max_charge < 0:
            raise ValueError("max_charge must be non-negative")
        self._estimator = estimator
        self._scale = scale
        self._rounding = rounding
        self._max_charge = max_charge

    def estimate_charge(
        self,
        model: str,
        usage: RelayUsage,
        *,
        provider: str = "",
        channel: str = "",
    ) -> Result[RelayChargeBreakdown, RelayBillingError]:
        """Estimate prompt and completion charges from the LLM estimator."""
        provider_arg = provider or None
        try:
            prompt_cost = float(
                self._estimator.estimate_cost(
                    model,
                    usage.prompt_tokens,
                    provider_arg,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=0,
                )
            )
            completion_cost = float(
                self._estimator.estimate_cost(
                    model,
                    usage.completion_tokens,
                    provider_arg,
                    prompt_tokens=0,
                    completion_tokens=usage.completion_tokens,
                )
            )
        except (TypeError, ValueError, OverflowError) as exc:
            return Err(invalid_usage(message=f"estimator failed: {exc}"))
        prompt = Decimal(str(prompt_cost))
        completion = Decimal(str(completion_cost))
        if not prompt.is_finite() or not completion.is_finite():
            return Err(invalid_usage(message="estimator returned a non-finite cost"))
        if prompt < 0 or completion < 0:
            return Err(invalid_usage(message="estimator returned a negative cost"))
        quantum = Decimal(1).scaleb(-self._scale)
        try:
            prompt = prompt.quantize(quantum, rounding=self._rounding)
            completion = completion.quantize(quantum, rounding=self._rounding)
        except DecimalException:
            return Err(invalid_usage(message="charge rounding failed"))
        zero = Decimal(0)
        total = prompt + completion
        if total > self._max_charge:
            return Err(
                charge_overflow(
                    message=f"charge {total} exceeds configured maximum {self._max_charge}"
                )
            )
        return Ok(
            RelayChargeBreakdown(
                prompt=prompt,
                cached_prompt=zero,
                completion=completion,
                reasoning=zero,
                audio_input=zero,
                audio_output=zero,
                image=zero,
                total=total,
            )
        )
