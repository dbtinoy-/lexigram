"""Admin dashboard sub-provider — assembles dashboard from contributors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.admin.contributors.registry import ContributorRegistry
from lexigram.admin.dashboard.assembler import DashboardAssembler
from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.admin.dashboard.page_assembler import PageAssembler
from lexigram.admin.dashboard.permission_filter import PermissionFilter
from lexigram.admin.dashboard.settings_assembler import SettingsPanelAssembler
from lexigram.admin.dashboard.widgets import WidgetRegistry
from lexigram.contracts.admin.protocols import AdminDashboardProtocol
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class AdminDashboardSubProvider:
    """Manages dashboard assembly from contributor definitions."""

    def __init__(
        self,
        config: AdminConfig,
        contributor_registry: ContributorRegistry,
    ) -> None:
        self._config = config
        self._registry = contributor_registry
        self._assembler: DashboardAssembler | None = None

    @property
    def config(self) -> AdminConfig:
        """Return current admin config."""
        return self._config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register dashboard assembler and services in the DI container."""
        from lexigram.admin.services.charts import ChartFactory
        from lexigram.admin.services.user_dashboard import UserDashboardService

        naming = NamingPolicy(mode=self._config.contributor_collision_mode)
        perms = PermissionFilter()
        page_asm = PageAssembler(naming_policy=naming, permission_filter=perms)
        settings_asm = SettingsPanelAssembler(
            naming_policy=naming, permission_filter=perms
        )

        self._assembler = DashboardAssembler(
            contributors=list(self._registry.get_all()),
            page_assembler=page_asm,
            settings_assembler=settings_asm,
        )
        container.singleton(AdminDashboardProtocol, self._assembler)
        container.singleton(DashboardAssembler, self._assembler)

        # Pre-construct to avoid the container trying to resolve `Any` as a
        # dependency type (builder defaults to None, which is fine).
        container.singleton(UserDashboardService, UserDashboardService())
        container.singleton(ChartFactory, ChartFactory())
        container.singleton(WidgetRegistry, WidgetRegistry())

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Dashboard boot — no additional init required."""

    async def shutdown(self) -> None:
        """Dashboard shutdown."""
        self._assembler = None

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return dashboard assembly health."""
        return HealthCheckResult(
            component="admin_dashboard",
            status=HealthStatus.HEALTHY if self._assembler else HealthStatus.UNKNOWN,
            message="Dashboard assembler ready"
            if self._assembler
            else "Not initialized",
        )


__all__ = ["AdminDashboardSubProvider"]
