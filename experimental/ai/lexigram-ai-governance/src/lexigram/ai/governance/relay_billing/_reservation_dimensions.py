"""Scope-dimension helpers for relay billing reservations.

Defines the relay quota scope dimensions (tenant, account, user, model,
provider, channel), their configured limits, and the prompt/output token
estimation used for admission control. The reservation manager consumes
these helpers; window bookkeeping lives in
:mod:`lexigram.ai.governance.relay_billing.reservations`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from lexigram.contracts.ai.relay import (
    ClaudeRequest,
    GeminiRequest,
    OpenAIChatRequest,
    RelayRequestPayload,
    ResponsesRequest,
)
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str

if TYPE_CHECKING:
    from lexigram.contracts.ai.governance import RelayUsageScope
    from lexigram.contracts.ai.llm import TokenCounterProtocol

logger = get_logger(__name__)

__all__ = [
    "DEFAULT_WINDOW_SECONDS",
    "RELAY_DIMENSIONS",
    "RelayReservationLimits",
    "RelayScopeLimit",
    "estimate_prompt_tokens",
    "requested_max_output_tokens",
    "scope_keys",
    "scope_value",
]

RELAY_DIMENSIONS = ("tenant", "account", "user", "model", "provider", "channel")
DEFAULT_WINDOW_SECONDS = 60.0
_CHARS_PER_TOKEN = 4


@dataclass(frozen=True, slots=True)
class RelayScopeLimit:
    """Admission quota for one scope dimension.

    Attributes:
        max_tokens: Maximum tokens admitted in the sliding window.
        max_charge: Maximum charge admitted in the sliding window.
        window_seconds: Sliding window size in seconds.
    """

    max_tokens: int
    max_charge: Decimal
    window_seconds: float = DEFAULT_WINDOW_SECONDS

    def __post_init__(self) -> None:
        """Reject negative token/charge limits or a non-positive window."""
        if self.max_tokens < 0:
            raise ValueError("max_tokens must be non-negative")
        if self.max_charge < 0:
            raise ValueError("max_charge must be non-negative")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass(frozen=True, slots=True)
class RelayReservationLimits:
    """Configured per-dimension admission limits.

    Attributes:
        tenant: Tenant-scope limit, when enforced.
        account: Account-scope limit, when enforced.
        user: User-scope limit, when enforced.
        model: Model-scope limit, when enforced.
        provider: Provider-scope limit, when enforced.
        channel: Channel-scope limit, when enforced.
    """

    tenant: RelayScopeLimit | None = None
    account: RelayScopeLimit | None = None
    user: RelayScopeLimit | None = None
    model: RelayScopeLimit | None = None
    provider: RelayScopeLimit | None = None
    channel: RelayScopeLimit | None = None


def scope_value(scope: RelayUsageScope, dimension: str) -> str:
    """Return the value of a dimension in *scope* (``""`` if unset)."""
    if dimension == "tenant":
        return scope.tenant_id
    if dimension == "model":
        return scope.model
    if dimension == "provider":
        return scope.provider
    if dimension == "channel":
        return scope.channel
    if dimension == "account":
        return scope.account_id or ""
    return scope.user_id or ""


def scope_keys(limits: RelayReservationLimits, scope: RelayUsageScope) -> list[str]:
    """Collect internal window keys for the configured scope.

    Args:
        limits: Per-dimension quota configuration.
        scope: The scope to map onto configured dimensions.

    Returns:
        Window keys ``"<dim>:<value>"`` for every configured
        dimension the scope carries a value for.
    """
    keys: list[str] = []
    for dimension in RELAY_DIMENSIONS:
        limit = getattr(limits, dimension)
        if limit is None:
            continue
        value = scope_value(scope, dimension)
        if not value:
            logger.debug(
                "relay_reservation_scope_empty",
                dimension=dimension,
                tenant_id=scope.tenant_id,
            )
            continue
        keys.append(f"{dimension}:{value}")
    return keys


def _payload_text(payload: RelayRequestPayload) -> str:
    """Serialize a request payload to a JSON text for estimation."""
    return dumps_str(payload.to_dict())


def estimate_prompt_tokens(
    payload: RelayRequestPayload,
    token_counter: TokenCounterProtocol | None = None,
) -> int:
    """Estimate the prompt token count for a request payload.

    Args:
        payload: Relay request payload to estimate.
        token_counter: Optional model-aware token counter; when provided
            it counts the serialized payload, otherwise the character
            estimate (~4 chars per token) is used.

    Returns:
        A non-negative, admission-only token estimate.
    """
    text = _payload_text(payload)
    if token_counter is not None:
        return max(0, int(token_counter.count(text)))
    return max(1, len(text) // _CHARS_PER_TOKEN)


def requested_max_output_tokens(payload: RelayRequestPayload) -> int:
    """Return the requested max output tokens, or 0 when not set.

    Args:
        payload: Relay request payload to inspect.

    Returns:
        The requested output budget, or 0 when the request does not
        carry one.
    """
    if isinstance(payload, OpenAIChatRequest):
        value = payload.max_completion_tokens or payload.max_tokens
        return value or 0
    if isinstance(payload, ResponsesRequest):
        return payload.max_output_tokens or 0
    if isinstance(payload, ClaudeRequest):
        return payload.max_tokens
    if isinstance(payload, GeminiRequest):
        value = payload.generation_config.get("maxOutputTokens")
        if value is None:
            value = payload.generation_config.get("max_output_tokens")
        return int(value) if value is not None else 0
    return 0
