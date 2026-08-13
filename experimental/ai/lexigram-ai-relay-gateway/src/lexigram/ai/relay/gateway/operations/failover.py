"""Reactive failover tracking for the relay gateway.

``RelayFailoverTracker`` turns consecutive upstream failures into runtime
selection state: a channel that fails ``threshold`` times in a row is
taken out of service through the registry's runtime overrides, and the
next successful dispatch on that channel restores it.  The tracker only
restores channels it disabled itself — an operator drain through the
permissioned controls surface is never silently reversed (mirroring the
auto-tester's journal semantics).

Failures are recorded per channel and reset on success; the tracker never
reads request payloads and holds no upstream details.

Deliberate divergence from ``lexigram-resilience``: this tracker does not
reuse ``CircuitBreaker``.  Gateway failures are ``Result``-based
``RelayGatewayError`` values, not exceptions, and the breaker's state is
not shared with the runtime overrides that selection, the operator
controls surface, and the auto-tester all read.  Recovery also differs:
one successful dispatch restores, mirroring new-api.  If distributed ban
state is ever needed, add a storage protocol like
``CircuitBreakerBackend`` instead of growing in-memory semantics.
"""

from __future__ import annotations

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.logging import get_logger

__all__ = ["RelayFailoverTracker"]

logger = get_logger(__name__)


class RelayFailoverTracker:
    """Track consecutive upstream failures and ban failing channels.

    The tracker mutates only the registry's runtime enabled overrides,
    the same surface the operator controls and the auto-tester use.  The
    threshold is compared with ``>=`` so the ban happens on the attempt
    that reaches it.

    Args:
        registry: The channel registry whose runtime enable flags this
            tracker mutates.
        threshold: Consecutive failures that disable a channel.  Must be
            positive.
    """

    def __init__(
        self,
        registry: RelayChannelRegistry,
        threshold: int,
    ) -> None:
        """Bind the tracker to the registry and threshold.

        Args:
            registry: The channel registry receiving runtime transitions.
            threshold: Consecutive failures that disable a channel.
        """
        if threshold < 1:
            raise ValueError("threshold must be a positive integer")
        self._registry = registry
        self._threshold = threshold
        self._failures: dict[str, int] = {}
        self._banned: set[str] = set()

    @property
    def threshold(self) -> int:
        """Return the consecutive-failure threshold.

        Returns:
            The threshold configured at construction.
        """
        return self._threshold

    def failure_count(self, channel: str) -> int:
        """Return the recorded consecutive failures for *channel*.

        Args:
            channel: The channel name to inspect.

        Returns:
            The consecutive failure count, ``0`` when none recorded.
        """
        return self._failures.get(channel, 0)

    def banned(self) -> frozenset[str]:
        """Return the channels this tracker disabled.

        Returns:
            The immutable set of channel names banned by this tracker.
        """
        return frozenset(self._banned)

    def record_failure(self, channel: str) -> None:
        """Count one upstream failure for *channel* and ban at threshold.

        When the count reaches the threshold and the channel was not
        already banned, the channel is drained through the registry's
        runtime overrides and journaled as banned by this tracker.

        Args:
            channel: The channel name that failed upstream.
        """
        count = self._failures.get(channel, 0) + 1
        self._failures[channel] = count
        if count >= self._threshold and channel not in self._banned:
            self._registry.set_runtime_enabled(channel, False)
            self._banned.add(channel)
            logger.info(
                "relay_gateway_channel_banned",
                channel=channel,
                failures=count,
                threshold=self._threshold,
            )

    def record_success(self, channel: str) -> None:
        """Reset *channel*'s failures and restore it when banned here.

        A successful dispatch clears the consecutive-failure count; when
        this tracker had banned the channel, it is restored at runtime
        and removed from the ban journal.

        Args:
            channel: The channel name that succeeded upstream.
        """
        if channel in self._failures:
            del self._failures[channel]
        if channel in self._banned:
            self._registry.set_runtime_enabled(channel, True)
            self._banned.discard(channel)
            logger.info(
                "relay_gateway_channel_restored",
                channel=channel,
                reason="dispatch_recovered",
            )
