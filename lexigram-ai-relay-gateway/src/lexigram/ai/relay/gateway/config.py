"""Typed gateway configuration for the relay gateway.

Holds the static channel table plus model-suffix and provider-options
metadata. The suffix and option maps are consumed at conversion time by
the service layer; channel selection never reads them. The auto-test
flags control the background channel health sweep (see
:class:`~lexigram.ai.relay.gateway.operations.auto_test.RelayChannelAutoTester`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from lexigram.contracts.ai.relay import JsonValue, RelayChannel, RelayFormat

__all__ = ["RelayGatewayConfig"]

_CHANNEL_FIELDS = {
    "name",
    "upstream_base_url",
    "target_format",
    "models",
    "capabilities",
    "endpoint_kinds",
    "priority",
    "weight",
    "enabled",
    "timeout_seconds",
    "model_map",
}
"""Channel keys accepted by :meth:`RelayGatewayConfig.from_mapping`."""


@dataclass(frozen=True, slots=True)
class RelayGatewayConfig:
    """Static configuration backing ``RelayChannelRegistry`` selection.

    Attributes:
        channels: The ordered channel configurations. Selection filters
            before sorting, so order is never observable in the result
            except as the stable ``name`` tiebreak. Duplicate names are
            rejected.
        model_suffix: Channel name to a suffix (e.g. ``":thinking"``)
            appended to the outbound model alias at the service layer.
            Selection does not use this field.
        provider_options: Channel name to provider-specific options merged
            into ``RelayConversionContext`` at conversion time. Selection
            does not use this field.
        auto_test_channels: When ``True`` the provider starts a background
            channel auto-tester that periodically probes every channel
            and disables failed ones, re-enabling them on recovery.
            Defaults to ``False`` (disabled).
        auto_test_interval_seconds: Delay between auto-test sweeps in
            seconds. Must be positive when defined. Defaults to ``600``.
        max_upstream_retries: Number of retry attempts across *other*
            channels after a retryable upstream failure on the buffered
            path. Defaults to ``0`` (single attempt, today's behavior).
        load_balancing: Channel-selection mode. ``"deterministic"``
            (default) keeps today's name-sort tiebreak; ``"weighted"``
            breaks ties among equal-priority eligible channels by
            weighted-random pick driven by each channel's ``weight``.
        job_ttl_seconds: Age in seconds after which a relay job record
            (``POST /v1/videos`` style job relay) is evicted from the
            in-memory job registry on its next poll. Must be positive.
            Defaults to ``3600`` (one hour).
        require_auth: When ``True`` the inbound relay routes require a
            bound ``RelayAuthVerifierProtocol``; when ``False`` (default)
            all routes stay open, preserving today's behavior.
        rate_limits: Model name (or ``"*"`` for the token-wide rule) to
            a ``{"max": int, "window_seconds": int}`` budget.  Empty
            (default) disables the rate-limit guard entirely.
        auto_disable_on_failures: When ``True`` the gateway tracks
            consecutive upstream failures per channel and takes a channel
            out of service at runtime once ``failover_failure_threshold``
            is reached, restoring it after the next successful dispatch.
            Defaults to ``False`` (disabled).
        failover_failure_threshold: Number of consecutive failures that
            disable a channel when ``auto_disable_on_failures`` is on.
            Defaults to ``3``.
    """

    channels: tuple[RelayChannel, ...] = ()
    model_suffix: Mapping[str, str] = field(default_factory=dict)
    provider_options: Mapping[str, Mapping[str, JsonValue]] = field(
        default_factory=dict
    )
    auto_test_channels: bool = False
    auto_test_interval_seconds: int = 600
    max_upstream_retries: int = 0
    load_balancing: Literal["deterministic", "weighted"] = "deterministic"
    job_ttl_seconds: int = 3600
    require_auth: bool = False
    rate_limits: Mapping[str, Mapping[str, int]] = field(default_factory=dict)
    auto_disable_on_failures: bool = False
    failover_failure_threshold: int = 3

    def __post_init__(self) -> None:
        """Reject duplicate names, bad auto-test intervals, and negative retries."""
        names = [channel.name for channel in self.channels]
        if len(names) != len(set(names)):
            raise ValueError("duplicate channel names in RelayGatewayConfig")
        if self.auto_test_interval_seconds <= 0:
            raise ValueError("auto_test_interval_seconds must be a positive integer")
        if self.max_upstream_retries < 0:
            raise ValueError("max_upstream_retries must be non-negative")
        if self.load_balancing not in ("deterministic", "weighted"):
            raise ValueError("load_balancing must be 'deterministic' or 'weighted'")
        if self.job_ttl_seconds <= 0:
            raise ValueError("job_ttl_seconds must be a positive integer")
        if self.failover_failure_threshold < 1:
            raise ValueError("failover_failure_threshold must be a positive integer")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> RelayGatewayConfig:
        """Build the configuration from a JSON/TOML-style mapping.

        Channel entries accept the fields of :class:`RelayChannel`
        (``target_format`` as the format member name, e.g.
        ``"OPENAI_CHAT"``), and top-level keys mirror the remaining
        attributes of this class. Unknown channel keys and top-level
        ``"channels"`` types raise ``ValueError`` with the offending
        key named.

        Args:
            data: Mapping with a ``"channels"`` list and optional
                gateway fields.

        Returns:
            A validated ``RelayGatewayConfig``.

        Raises:
            TypeError: On malformed channel entries or a non-list
                ``"channels"`` value.
            ValueError: On unknown channel keys or invalid top-level
                values.
        """
        raw_channels = data.get("channels", ())
        if isinstance(raw_channels, Mapping):
            raise TypeError("channels must be a list of channel mappings")
        channels: list[RelayChannel] = []
        for index, entry in enumerate(raw_channels):
            if not isinstance(entry, Mapping):
                raise TypeError(f"channels[{index}] must be an object")
            unknown = set(entry) - _CHANNEL_FIELDS
            if unknown:
                raise ValueError(
                    f"channels[{index}] has unknown keys: {sorted(unknown)}"
                )
            channels.append(cls._channel_from_mapping(entry))
        allowed = {
            "channels",
            "model_suffix",
            "provider_options",
            "auto_test_channels",
            "auto_test_interval_seconds",
            "max_upstream_retries",
            "load_balancing",
            "job_ttl_seconds",
            "require_auth",
            "rate_limits",
            "auto_disable_on_failures",
            "failover_failure_threshold",
        }
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown gateway config keys: {sorted(unknown)}")
        return cls(
            channels=tuple(channels),
            model_suffix=dict(data.get("model_suffix", {}) or {}),
            provider_options=dict(data.get("provider_options", {}) or {}),
            auto_test_channels=bool(data.get("auto_test_channels", False)),
            auto_test_interval_seconds=int(data.get("auto_test_interval_seconds", 600)),
            max_upstream_retries=int(data.get("max_upstream_retries", 0)),
            load_balancing=data.get("load_balancing", "deterministic"),
            job_ttl_seconds=int(data.get("job_ttl_seconds", 3600)),
            require_auth=bool(data.get("require_auth", False)),
            rate_limits=dict(data.get("rate_limits", {}) or {}),
            auto_disable_on_failures=bool(data.get("auto_disable_on_failures", False)),
            failover_failure_threshold=int(data.get("failover_failure_threshold", 3)),
        )

    @staticmethod
    def _channel_from_mapping(entry: Mapping[str, Any]) -> RelayChannel:
        """Build one ``RelayChannel`` from a validated mapping entry."""
        missing = {"name", "upstream_base_url", "target_format", "models"} - set(entry)
        if missing:
            raise ValueError(f"channel object missing keys: {sorted(missing)}")
        raw_format = entry["target_format"]
        try:
            target_format = RelayFormat[raw_format]  # member name
        except (KeyError, TypeError):
            try:
                target_format = RelayFormat(raw_format)  # member value
            except ValueError as exc:
                raise ValueError(
                    f"unknown target_format {raw_format!r}; "
                    f"expected one of {[m.value for m in RelayFormat]}"
                ) from exc
        return RelayChannel(
            name=str(entry["name"]),
            upstream_base_url=str(entry["upstream_base_url"]),
            target_format=target_format,
            models=tuple(entry["models"]),
            capabilities=frozenset(entry.get("capabilities", ()) or ()),
            endpoint_kinds=frozenset(entry.get("endpoint_kinds", ()) or ()),
            priority=int(entry.get("priority", 100)),
            weight=int(entry.get("weight", 100)),
            enabled=bool(entry.get("enabled", True)),
            timeout_seconds=float(entry.get("timeout_seconds", 60.0)),
            model_map=dict(entry.get("model_map", {}) or {}),
        )
