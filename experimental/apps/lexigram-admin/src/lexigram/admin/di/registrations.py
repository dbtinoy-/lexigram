"""Built-in singleton registrations for the admin bundle provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerRegistrarProtocol

_log = get_logger(__name__)


def register_builtin_singletons(
    container: ContainerRegistrarProtocol,
    controllers: list[type],
    resources: list[type],
) -> None:
    """Register the admin built-in controllers and services as singletons.

    Registers the widget/tenancy/dashboard controllers, impersonation
    services, and the RBAC permission inventory, then registers every
    user-supplied controller and resource class so the container can inject
    their service dependencies. Re-registration is expected and only logged.

    Args:
        container: The DI registrar to bind singletons on.
        controllers: User-supplied controller classes.
        resources: User-supplied resource classes.
    """
    from lexigram.admin.controllers.dashboard import DashboardController
    from lexigram.admin.controllers.impersonation import ImpersonationController
    from lexigram.admin.controllers.tenancy import TenancyController
    from lexigram.admin.controllers.widgets import WidgetController

    # Register built-in controllers
    container.singleton(WidgetController, WidgetController)
    container.singleton(TenancyController, TenancyController)
    container.singleton(DashboardController, DashboardController)
    from lexigram.admin.services.impersonation import ImpersonationService

    container.singleton(ImpersonationService, ImpersonationService)
    container.singleton(ImpersonationController, ImpersonationController)
    # Register the RBAC permission inventory (populated at mount time)
    from lexigram.admin.rbac.inventory import PermissionInventoryService

    container.singleton(PermissionInventoryService, PermissionInventoryService)
    # Register controller classes for DI resolution
    for controller_cls in controllers:
        try:
            container.singleton(controller_cls, controller_cls)
        except Exception:  # noqa: BLE001 — re-registration is expected; continue loop
            _log.debug(
                "admin.controller_already_registered",
                controller=controller_cls.__name__,
            )
    # Register resource classes so the container can inject their service dependencies
    for resource_cls in resources:
        try:
            container.singleton(resource_cls, resource_cls)
        except Exception:  # noqa: BLE001 — re-registration is expected; continue loop
            _log.debug(
                "admin.resource_already_registered", resource=resource_cls.__name__
            )


__all__ = ["register_builtin_singletons"]
