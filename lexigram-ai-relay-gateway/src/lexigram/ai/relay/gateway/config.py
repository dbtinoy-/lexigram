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
from typing import Literal

from lexigram.contracts.ai.relay import JsonValue, RelayChannel

__all__ = ["RelayGatewayConfig"]


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
