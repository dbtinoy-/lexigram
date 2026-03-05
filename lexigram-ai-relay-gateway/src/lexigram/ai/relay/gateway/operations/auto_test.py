"""Background auto-tester for relay gateway channel health.

``RelayChannelAutoTester`` periodically runs one channel health sweep and
translates probe outcomes into runtime selection state: channels that
continuously fail are disabled at runtime, and channels that the tester
itself took down are re-enabled once their probe comes back healthy.
The tester never restores a channel a human admin drained through the
permissioned actuator surface — only its own disables are tracked and
reversed.
"""

from __future__ import annotations

import asyncio

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.contracts.ai.relay import RelayChannelHealth
from lexigram.logging import get_logger

__all__ = ["RelayChannelAutoTester"]

logger = get_logger(__name__)

_HEALTHY_STATUS = "healthy"
_UNHEALTHY_STATUSES = frozenset({"failed"})
"""Channel statuses treated by the auto-tester as failing probes."""


class RelayChannelAutoTester:
    """Automatically disable failing channels and restore recovered ones.

    The tester runs as its own ``asyncio.Task``, taking one health
    snapshot per interval and turning probe outcomes into runtime
    transitions via ``RelayChannelRegistry.set_runtime_enabled``. Its
    own disable decisions are journaled in ``_disabled_by_tester`` so a
    channel drained by a human through the actuator controls is never
    silently restored.

    Args:
        health: The health service that produces per-channel snapshots.
        registry: The channel registry whose runtime enable flags this
            tester mutates.
        interval_seconds: Whole seconds between two consecutive sweeps.
            Must be positive.
    """

    def __init__(
        self,
        health: RelayHealthService,
        registry: RelayChannelRegistry,
        interval_seconds: float,
    ) -> None:
        """Bind the auto-tester to its health service and registry.

        Args:
            health: Health service whose snapshots drive the sweep.
            registry: Channel registry receiving runtime transitions.
            interval_seconds: Delay between sweeps, in whole seconds.
        """
        self._health = health
        self._registry = registry
        self._interval_seconds = interval_seconds
        self._disabled_by_tester: set[str] = set()
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        """Return whether a sweep loop is currently scheduled.

        Returns:
            ``True`` when ``start()`` has scheduled a task that has not
            gone away, ``False`` otherwise.
        """
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start the periodic sweep; a no-op when one is already running.

        The first sweep runs immediately after scheduling, then the loop
        sleeps ``interval_seconds`` between iterations.
        """
        if self.is_running:
            return
        self._task = asyncio.create_task(self._sweep_loop(), name="relay-auto-test")

    async def stop(self) -> None:
        """Cancel the sweep loop and await its completion.

        Idempotent: calling stop when nothing is running is a no-op.
        """
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def sweep(self) -> None:
        """Run one probe sweep and apply the resulting transitions.

        The snapshots come from the health service as-is; the sweep does
        not probe channels on its own. An exception raised while the
        health service probes a channel is caught and logged per sweep,
        and the loop continues to its next iteration.

        Example:
            ```python
            await tester.sweep()
            ```
        """
        try:
            snapshots = await self._health.channel_health()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "relay_gateway_channel_auto_sweep_failed",
                error=str(exc),
            )
            return
        await self._apply(list(snapshots))

    async def _sweep_loop(self) -> None:
        """Repeat ``sweep()`` then idle ``interval_seconds`` forever."""
        while True:
            try:
                await self.sweep()
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "relay_gateway_channel_auto_loop_failed",
                    error=str(exc),
                )
            await asyncio.sleep(self._interval_seconds)

    async def _apply(self, snapshots: list[RelayChannelHealth]) -> None:
        """Diff *snapshots* against the journal and update the registry.

        Args:
            snapshots: One snapshot per configured channel, in config
                order, from the health service.
        """
        by_name = {snapshot.channel: snapshot for snapshot in snapshots}
        for channel_name in list(self._disabled_by_tester):
            snapshot = by_name.get(channel_name)
            if snapshot is not None and snapshot.status == _HEALTHY_STATUS:
                self._recover(channel_name)
        for snapshot in snapshots:
            if (
                snapshot.status in _UNHEALTHY_STATUSES
                and snapshot.channel not in self._disabled_by_tester
            ):
                self._disable(snapshot.channel)

    def _disable(self, channel_name: str) -> None:
        """Take *channel_name* out of service and journal the decision.

        Args:
            channel_name: The channel to disable at runtime.
        """
        self._registry.set_runtime_enabled(channel_name, False)
        self._disabled_by_tester.add(channel_name)
        logger.info(
            "relay_gateway_channel_auto_disabled",
            channel=channel_name,
            reason="probe_failed",
        )

    def _recover(self, channel_name: str) -> None:
        """Restore *channel_name* at runtime; the journal entry is removed.

        Args:
            channel_name: The channel previously disabled by this tester.
        """
        self._registry.set_runtime_enabled(channel_name, True)
        self._disabled_by_tester.discard(channel_name)
        logger.info(
            "relay_gateway_channel_auto_reenabled",
            channel=channel_name,
            reason="probe_recovered",
        )
