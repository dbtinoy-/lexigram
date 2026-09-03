"""Read-model over mounted admin resources for dashboard consumption.

The mount pipeline materializes resource instances (with wired data
sources) into ``MountContext.resources`` — a surface that contributors
never see, because they only receive the DI container at boot time,
before resources exist. :class:`ResourceInventory` bridges that gap: it
is built once at mount time over the live resources mapping and pushed
to every contributor that exposes a ``set_resource_inventory`` hook.

Consumers get a fail-soft :meth:`ResourceInventory.snapshot` of
per-resource record counts suitable for stat widgets; individual count
failures never break the snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)

#: Default maximum number of resources included in a snapshot.
DEFAULT_SNAPSHOT_LIMIT = 8


@dataclass(frozen=True, slots=True)
class ResourceCount:
    """A single resource's display metadata and record count.

    ``count`` is ``None`` when the resource has no usable data source or
    counting failed — renderers should show a placeholder (``—``) rather
    than dropping the resource from the overview.
    """

    name: str
    label: str
    icon: str
    count: int | None


class ResourceInventory:
    """Countable view over the mounted resource instances.

    Holds a *reference* to the live resources mapping populated by the
    mount pipeline, so resources wired after construction (for example
    contributor resources collected later in the same mount pass) are
    visible without re-wiring.
    """

    def __init__(self, resources: Mapping[str, Any]) -> None:
        """Capture the live mapping of resource name to resource instance.

        Args:
            resources: Mapping of mounted resource name → resource
                instance, typically ``MountContext.resources``.
        """
        self._resources = resources

    def is_empty(self) -> bool:
        """Return True when no resources are mounted."""
        return not self._resources

    async def snapshot(
        self, limit: int = DEFAULT_SNAPSHOT_LIMIT
    ) -> tuple[ResourceCount, ...]:
        """Return per-resource record counts in mount (sidebar) order.

        Every resource up to ``limit`` is included; resources whose count
        cannot be determined carry ``count=None``. This method never
        raises — data-source failures are logged at debug level and
        rendered as unavailable.

        Args:
            limit: Maximum number of resources to include.

        Returns:
            Tuple of :class:`ResourceCount` in mapping insertion order.
        """
        out: list[ResourceCount] = []
        for name, resource in list(self._resources.items())[: max(limit, 0)]:
            out.append(
                ResourceCount(
                    name=name,
                    label=self._label_for(name, resource),
                    icon=str(getattr(resource, "icon", None) or "box"),
                    count=await self._count_for(name, resource),
                )
            )
        return tuple(out)

    @staticmethod
    def _label_for(name: str, resource: Any) -> str:
        """Pick a display label: meta plural → resource label → titled name."""
        meta = getattr(resource, "meta", None)
        label = getattr(meta, "label_plural", None) or getattr(
            resource, "label", None
        )
        if label:
            return str(label)
        return name.replace("_", " ").replace("-", " ").title()

    @staticmethod
    async def _count_for(name: str, resource: Any) -> int | None:
        """Count records for one resource, fail-soft.

        Uses the canonical data-source accessor so wired, lazily-provided,
        and legacy-service sources are all handled. Sources without a
        ``count`` method fall back to ``find_many(...).total``.
        """
        from lexigram.admin.data.query import QuerySpec
        from lexigram.admin.resources.data_access import get_resource_data_source

        try:
            data_source = get_resource_data_source(resource)
        except Exception:  # noqa: BLE001 — accessor is best-effort here
            logger.debug("admin.resource_count_source_failed", resource=name)
            return None
        if data_source is None:
            return None

        query = QuerySpec(page=1, per_page=1)
        try:
            counter = getattr(data_source, "count", None)
            if callable(counter):
                return int(await counter(query))
            result = await data_source.find_many(query)
            total = getattr(result, "total", None)
            return int(total) if total is not None else None
        except Exception as exc:  # noqa: BLE001 — one bad source must not
            # take down the whole overview widget.
            logger.debug(
                "admin.resource_count_failed", resource=name, error=str(exc)
            )
            return None


__all__ = ["DEFAULT_SNAPSHOT_LIMIT", "ResourceCount", "ResourceInventory"]
