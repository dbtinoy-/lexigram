"""Deterministic channel selection for the relay gateway.

Selection is a pure function of the static channel table and the routing
intent: source format, model alias, streaming flag, requested capability
flags, and an optional preferred channel. The registry never inspects
request payloads to make an undocumented routing decision.
"""

from __future__ import annotations

from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.contracts.ai.relay import RelayChannel, RelayFormat, RelayGatewayError
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = ["RelayChannelRegistry"]


class RelayChannelRegistry:
    """Selects a ``RelayChannel`` deterministically from a static config.

    Note:
        "Healthy channel" in the plan is interpreted as the channel's
        ``enabled`` flag; there is no separate health field in this
        milestone.

    Attributes:
        _channels: The immutable channel table from ``RelayGatewayConfig``.
    """

    def __init__(self, config: RelayGatewayConfig) -> None:
        """Bind the registry to a static channel table.

        Args:
            config: Immutable gateway configuration. Selection never
                mutates it; the channel tuple is kept as configured.
        """
        self._channels = config.channels

    def select(
        self,
        source: RelayFormat,
        model: str,
        stream: bool = False,
        capabilities: frozenset[str] = frozenset(),
        preferred: str | None = None,
    ) -> Result[RelayChannel, RelayGatewayError]:
        """Pick the best channel for the routing query.

        Eligibility is computed first (enabled, target format differs
        from the source, model serves the requested alias, streaming and
        capability constraints), then the survivors are sorted: preferred
        channel first, then exact model match, then ascending priority
        (lower number wins), then ascending name as a stable tiebreak.
        The preferred channel still must pass every eligibility filter;
        otherwise it is skipped and normal ordering applies.

        Args:
            source: Wire format the caller supplies; channels whose
                target format equals it would be no-op conversions and
                are never eligible.
            model: Requested model alias; only exact matches are
                eligible.
            stream: Whether the caller wants streaming. Channels that
                declare capabilities must declare ``"stream"`` to serve
                streaming requests; channels with no declared
                capabilities are unconstrained.
            capabilities: Requested capability flags; they must be a
                subset of the channel's declared capabilities.
            preferred: Optional channel name that ranks first when it is
                eligible. Defaults to ``None`` (no preference).

        Returns:
            ``Ok(channel)`` for the best eligible channel, or
            ``Err(RelayGatewayError)`` when none is eligible. The error
            cause is classified in fixed order: no enabled channels
            (``CHANNEL_DISABLED``, 404), no enabled channel transforms
            the source format (``TARGET_FORMAT_UNSUPPORTED``, 500), no
            enabled channel satisfies the capability filters
            (``CAPABILITY_UNAVAILABLE``, 409), otherwise the model is
            not served (``MODEL_NOT_FOUND``, 404).

        Note:
            Channel "health" is the ``enabled`` flag; no separate health
            signal exists in this milestone.
        """
        enabled = [channel for channel in self._channels if channel.enabled]
        if not enabled:
            return Err(
                RelayGatewayError(
                    code="CHANNEL_DISABLED",
                    message="no enabled channels",
                    status_code=404,
                    request_id="",
                )
            )
        transformable = [
            channel for channel in enabled if channel.target_format != source
        ]
        if not transformable:
            return Err(
                RelayGatewayError(
                    code="TARGET_FORMAT_UNSUPPORTED",
                    message="no channel supports the requested target format",
                    status_code=500,
                    request_id="",
                )
            )
        capable = [
            channel
            for channel in transformable
            if self._meets_capabilities(channel, stream, capabilities)
        ]
        if not capable:
            return Err(
                RelayGatewayError(
                    code="CAPABILITY_UNAVAILABLE",
                    message="no channel provides the requested capabilities",
                    status_code=409,
                    request_id="",
                )
            )
        matched = [channel for channel in capable if model in channel.models]
        if not matched:
            return Err(
                RelayGatewayError(
                    code="MODEL_NOT_FOUND",
                    message=f"no channel serves model {model!r}",
                    status_code=404,
                    request_id="",
                )
            )
        ordered = sorted(
            matched,
            key=lambda channel: (
                channel.name != preferred,
                model not in channel.models,
                channel.priority,
                channel.name,
            ),
        )
        return Ok(ordered[0])

    @staticmethod
    def _meets_capabilities(
        channel: RelayChannel, stream: bool, capabilities: frozenset[str]
    ) -> bool:
        """Check whether *channel* satisfies the streaming and capability filters."""
        if capabilities and not capabilities <= channel.capabilities:
            return False
        return not (
            stream and channel.capabilities and "stream" not in channel.capabilities
        )
