"""Deterministic channel selection for the relay gateway.

Selection is a pure function of the static channel table, the runtime
override table, and the routing intent: source format, model alias,
streaming flag, requested capability flags, and an optional preferred
channel. The registry never inspects request payloads to make an
undocumented routing decision.

The runtime override table is written by the operator controls surface
(``set_runtime_enabled``); it can only take a configured channel out of
service (drain) or restore it — it can never enable a channel whose
config ``enabled`` flag is false.
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
        ``enabled`` flag combined with the live runtime override table;
        drained channels are invisible to ``select`` until they are
        restored at runtime.

    Attributes:
        _channels: The immutable channel table from ``RelayGatewayConfig``.
        _runtime_enabled: Operator overrides applied by the controls
            service; empty equals "all channels as configured".
    """

    def __init__(self, config: RelayGatewayConfig) -> None:
        """Bind the registry to a static channel table.

        Args:
            config: Immutable gateway configuration. Selection never
                mutates it; the channel tuple is kept as configured.
        """
        self._channels = config.channels
        self._runtime_enabled: dict[str, bool] = {}

    @property
    def channels(self) -> tuple[RelayChannel, ...]:
        """The configured channel table.

        Returns:
            The immutable channel tuple, in configuration order.
        """
        return self._channels

    def set_runtime_enabled(self, channel: str, enabled: bool) -> None:
        """Override the eligibility of *channel* at runtime.

        Draining a channel (``enabled=False``) hides it from selection
        until restored; restoring removes the override entirely so the
        config ``enabled`` flag alone decides. A config-disabled channel
        can never be made eligible this way.

        Args:
            channel: Channel name to override.
            enabled: Whether the channel should select new requests.
        """
        if enabled:
            self._runtime_enabled.pop(channel, None)
        else:
            self._runtime_enabled[channel] = False

    def runtime_enabled(self) -> dict[str, bool]:
        """Return the non-default runtime overrides.

        Returns:
            Mapping of channel name to ``False`` set at runtime; a
            restored channel is absent.
        """
        return dict(self._runtime_enabled)

    def select(
        self,
        source: RelayFormat,
        model: str,
        stream: bool = False,
        capabilities: frozenset[str] = frozenset(),
        preferred: str | None = None,
    ) -> Result[RelayChannel, RelayGatewayError]:
        """Pick the best channel for the routing query.

        Eligibility is computed first (enabled by config and runtime,
        target format differs from the source, model serves the
        requested alias, streaming and capability constraints), then the
        survivors are sorted: preferred channel first, then exact model
        match, then ascending priority (lower number wins), then
        ascending name as a stable tiebreak.
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
            Runtime-drained channels are treated exactly like disabled
            channels: they are invisible to selection until restored.
        """
        enabled = self._enabled_channels()
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

    def select_for_endpoint(
        self,
        kind: str,
        model: str,
        *,
        exclude: frozenset[str] = frozenset(),
    ) -> Result[RelayChannel, RelayGatewayError]:
        """Pick the best channel serving an endpoint kind (e.g. ``"embeddings"``).

        Passthrough entry point: eligibility is limited to channels
        declaring *kind* in ``endpoint_kinds`` (empty means chat-only,
        never eligible here), then survivors are sorted by ascending
        priority (lower number wins) and ascending name as a stable
        tiebreak. Model aliases and the ``enabled``/runtime-disabled
        filters behave exactly like ``select``. A chat-only channel is
        untouched by this method.

        Args:
            kind: Endpoint kind the caller wants (e.g. ``"embeddings"``);
                only channels declaring it are eligible.
            model: Requested model alias; only exact matches are
                eligible.
            exclude: Channel names to skip, e.g. for failover retries.
                Defaults to empty (no exclusion).

        Returns:
            ``Ok(channel)`` for the best eligible channel, or
            ``Err(RelayGatewayError)`` when none is eligible: no enabled
            channels (``CHANNEL_DISABLED``, 404), otherwise, no channel
            serves the kind or model (``MODEL_NOT_FOUND``, 404).
        """
        enabled = self._enabled_channels()
        if not enabled:
            return Err(
                RelayGatewayError(
                    code="CHANNEL_DISABLED",
                    message="no enabled channels",
                    status_code=404,
                    request_id="",
                )
            )
        serving = [
            channel
            for channel in enabled
            if kind in channel.endpoint_kinds and channel.name not in exclude
        ]
        matched = [channel for channel in serving if model in channel.models]
        if not matched:
            return Err(
                RelayGatewayError(
                    code="MODEL_NOT_FOUND",
                    message=f"no channel serves endpoint {kind!r} for model {model!r}",
                    status_code=404,
                    request_id="",
                )
            )
        ordered = sorted(
            matched,
            key=lambda channel: (channel.priority, channel.name),
        )
        return Ok(ordered[0])

    def _enabled_channels(self) -> list[RelayChannel]:
        """Return channels enabled by both config and the runtime overrides."""
        return [
            channel
            for channel in self._channels
            if channel.enabled and self._runtime_enabled.get(channel.name, True)
        ]

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
