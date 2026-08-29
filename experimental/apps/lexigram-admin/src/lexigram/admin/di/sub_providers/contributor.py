"""Admin contributor sub-provider — discovers and manages admin contributors."""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

from lexigram.admin.contributors.core import CoreAdminContributor
from lexigram.admin.contributors.registry import ContributorRegistry
from lexigram.admin.contributors.resource_collector import ResourceCollector
from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.contracts.admin.dependencies import sort_contributors
from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.admin.protocols import AdminContributorProtocol
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)

ENTRY_POINT_GROUP = "lexigram.admin.contributors"


def _validate_widget_endpoints(
    contributors: list[Any],
    known_paths: set[str],
) -> None:
    """Log a warning for each widget whose render_endpoint has no matching route."""
    for c in contributors:
        try:
            widgets = c.get_dashboard_widgets()
        except Exception:  # noqa: BLE001
            logger.warning(
                "admin.widget_validation_get_widgets_failed",
                contributor=getattr(c, "name", repr(c)),
                exc_info=True,
            )
            continue
        for widget in widgets:
            ep = getattr(widget, "render_endpoint", None)
            if ep and ep not in known_paths:
                logger.warning(
                    "admin.widget_endpoint_not_registered",
                    contributor=getattr(c, "name", repr(c)),
                    widget=getattr(widget, "name", repr(widget)),
                    render_endpoint=ep,
                )


class AdminContributorSubProvider:
    """Discovers and manages admin contributors via entry points.

    Discovery order:
    1. Built-in CoreAdminContributor
    2. Entry points from ``lexigram.admin.contributors`` group
    3. Boot all enabled contributors

    When constructed with ``contributors``, the sub-provider operates in
    *direct mode*: ``boot_all()`` iterates those contributors, tracks any
    failures in ``_boot_failures``, and ``health_check()`` reflects that state.
    """

    def __init__(
        self,
        config: AdminConfig | None = None,
        contributors: list[AdminContributorProtocol] | None = None,
    ) -> None:
        self._config = config
        self._registry = ContributorRegistry()
        if config is not None:
            self._registry.add(CoreAdminContributor())
        self._direct_contributors: list[AdminContributorProtocol] = [
            c() if isinstance(c, type) else c for c in (contributors or [])
        ]
        self._boot_failures: dict[str, str] = {}
        self._entry_point_failures: dict[str, str] = {}
        self._collected_resources: list[type] = []
        self._collected_routes: list[Any] = []
        # Register direct contributors in the registry before entry-point
        # discovery so that entry points with the same name are skipped.
        for dc in self._direct_contributors:
            self._registry.add(dc)
        # Discover entry-point contributors here so that sub-providers
        # consuming the registry (e.g. AdminDashboardSubProvider) see
        # the full set during their own register() phase.
        self._discover_from_entry_points()

    @property
    def config(self) -> AdminConfig | None:
        """Return current admin config."""
        return self._config

    @property
    def registry(self) -> ContributorRegistry:
        """Return the contributor registry."""
        return self._registry

    @property
    def collected_resources(self) -> list[type]:
        """Return Resource classes collected from all contributors."""
        return list(self._collected_resources)

    @property
    def collected_routes(self) -> list[Any]:
        """Return AdminRouteSpec instances collected from all contributors at boot."""
        return list(self._collected_routes)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register the contributor registry in the DI container."""
        container.singleton(AdminContributorRegistryProtocol, self._registry)
        container.singleton(ContributorRegistry, self._registry)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot all discovered contributors, sorted by dependency order."""
        contributors = sort_contributors(self._registry.get_all())  # type: ignore[type-var]
        for contributor in contributors:
            if self._is_enabled(contributor.name):
                try:
                    await contributor.on_admin_boot(container)
                except Exception as exc:  # noqa: BLE001 — continue booting other contributors
                    logger.warning(
                        "admin.contributor_on_boot_failed",
                        contributor=contributor.name,
                        error=str(exc),
                        exc_info=True,
                    )
                    self._boot_failures[contributor.name] = str(exc)

    async def boot_all(self) -> None:
        """Boot directly-supplied contributors, tracking failures.

        Iterates every contributor passed to the constructor, calls
        ``await contributor.boot()``, and records the ``contributor_id``
        of any contributor whose boot raises.  Remaining contributors are
        always attempted — failures do not abort the loop.

        After booting, collects Resource classes from all contributors
        via ``ResourceCollector`` and stores them in ``_collected_resources``.
        """
        for contributor in self._direct_contributors:
            try:
                await contributor.on_admin_boot(None)  # type: ignore[arg-type]
            except Exception as exc:  # noqa: BLE001 — track failure and continue
                logger.error(
                    "admin.contributor_boot_failed",
                    contributor_id=contributor.contributor_id,
                    error=str(exc),
                )
                self._boot_failures[contributor.contributor_id] = str(exc)

        # Collect resources from all contributors (both direct and entry-point)
        try:
            all_contributors: list[AdminContributorProtocol] = list(
                self._registry.get_all()
            )
            all_contributors.extend(self._direct_contributors)

            naming = NamingPolicy(mode="warn")
            collector = ResourceCollector(naming_policy=naming)
            self._collected_resources = collector.collect(all_contributors)
        except Exception:  # noqa: BLE001 — resource collection is non-fatal
            logger.warning(
                "admin.contributor_resource_collection_failed", exc_info=True
            )

        # Collect routes from all contributors
        try:
            all_c: list[AdminContributorProtocol] = list(self._registry.get_all())
            all_c.extend(self._direct_contributors)
            for c in all_c:
                try:
                    for spec in c.get_routes():
                        self._collected_routes.append(spec)
                except Exception:  # noqa: BLE001 — skip broken contributors
                    logger.warning(
                        "admin.contributor_get_routes_failed",
                        contributor=getattr(c, "name", repr(c)),
                        exc_info=True,
                    )
        except Exception:  # noqa: BLE001 — route collection is non-fatal
            logger.warning("admin.contributor_route_collection_failed", exc_info=True)

        # Validate widget render_endpoint against collected routes
        try:
            known_paths = {spec.path for spec in self._collected_routes}
            all_contributors_for_validation: list = list(self._registry.get_all())
            all_contributors_for_validation.extend(self._direct_contributors)
            _validate_widget_endpoints(all_contributors_for_validation, known_paths)
        except Exception:  # noqa: BLE001 — validation is non-fatal
            logger.warning("admin.widget_endpoint_validation_failed", exc_info=True)

    async def shutdown(self) -> None:
        """Shut down all contributors in reverse priority order."""
        for contributor in reversed(list(self._registry.get_all())):
            try:
                await contributor.on_admin_shutdown()
            except Exception:  # noqa: BLE001 — continue shutting down other contributors
                logger.warning(
                    "admin.contributor_shutdown_failed",
                    contributor=contributor.name,
                    exc_info=True,
                )

    def health_check(self, timeout: float = 5.0) -> HealthCheckResult:  # noqa: ARG002
        """Return contributor health, reflecting any boot/entry-point failures.

        Args:
            timeout: Accepted for interface compatibility; unused by this
                synchronous implementation.

        Returns:
            ``DEGRADED`` with a failure summary when one or more contributors
            failed to boot; ``HEALTHY`` otherwise.
        """
        details: dict[str, object] = {}
        if self._entry_point_failures:
            details["entry_point_failures"] = dict(self._entry_point_failures)
        if self._boot_failures:
            details["boot_failures"] = dict(self._boot_failures)
        if self._entry_point_failures or self._boot_failures:
            return HealthCheckResult(
                component="admin_contributors",
                status=HealthStatus.DEGRADED,
                message=f"Boot failures: {self._boot_failures}, entry point failures: {self._entry_point_failures}",
                details=details,
            )
        count = len(list(self._registry.get_all())) + len(self._direct_contributors)
        return HealthCheckResult(
            component="admin_contributors",
            status=HealthStatus.HEALTHY,
            message=f"{count} contributor(s) registered",
            details={"count": count},
        )

    def _discover_from_entry_points(self) -> None:
        """Load contributors from the entry point group.

        Skips any contributor class that is already registered
        in the registry (i.e., was set up by a provider's factory).
        Only performs direct instantiation for zero-argument contributors
        that have no provider-based registration.
        """
        for ep in importlib.metadata.entry_points(group=ENTRY_POINT_GROUP):
            try:
                contributor_cls = ep.load()
                contributor = contributor_cls()
                # Skip if this contributor is already registered by a provider.
                # The provider's factory already constructed and registered it.
                if self._registry.get(contributor.name) is not None:
                    logger.debug(
                        "admin.contributor_already_registered",
                        name=contributor.name,
                    )
                    continue
                if self._is_enabled(contributor.name):
                    self._registry.add(contributor)
                    logger.info("contributor_discovered", name=contributor.name)
            except Exception as exc:  # noqa: BLE001 — skip bad entry points; continue discovery
                logger.warning(
                    "admin.entry_point_load_failed",
                    name=ep.name,
                    error=str(exc),
                    exc_info=True,
                )
                self._entry_point_failures[ep.name] = str(exc)

    def _is_enabled(self, name: str) -> bool:
        """Check if a contributor is enabled via config.

        Always returns ``True`` when no config was supplied (direct mode).
        """
        if self._config is None:
            return True
        contributors_config = getattr(self._config, "contributors", {})
        if isinstance(contributors_config, dict) and name in contributors_config:
            contrib_cfg = contributors_config[name]
            if isinstance(contrib_cfg, dict):
                return contrib_cfg.get("enabled", True)
            return getattr(contrib_cfg, "enabled", True)
        return True


__all__ = ["AdminContributorSubProvider"]
