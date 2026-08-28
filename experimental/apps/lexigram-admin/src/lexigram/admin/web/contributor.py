"""Admin web contributor for route and middleware registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.exceptions import UnresolvableDependencyError

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


class AdminWebContributor:
    """Web contributor for the admin package.

    Resolves and delegates to the AdminBundle's mount_to_app method
    if available. Does not contribute controllers or middleware directly;
    the bundle handles all mounting.
    """

    @property
    def contributor_id(self) -> str:
        """Return unique identifier for this contributor.

        Returns:
            The string "admin".
        """
        return "admin"

    def get_controllers(self) -> list[type[Any]]:
        """Return controllers contributed by the admin package.

        Admin uses the bundle pattern and does not contribute controllers directly.

        Returns:
            Empty list.
        """
        return []

    def get_middleware(self) -> list[type[Any]]:
        """Return middleware contributed by the admin package.

        Admin uses the bundle pattern and does not contribute middleware directly.

        Returns:
            Empty list.
        """
        return []

    async def mount_to_app(
        self, app: Any, container: ContainerResolverProtocol
    ) -> None:
        """Mount admin routes to the web application.

        Resolves the admin_bundle service (bypassing visibility checks)
        and delegates to its mount_to_app method if available.

        Args:
            app: The ASGI application (typically Starlette).
            container: DI container for resolving the admin bundle.
        """
        try:
            admin_bundle = await container.resolve(
                "admin_bundle", bypass_visibility=True
            )
        except UnresolvableDependencyError:
            # The web contributor is installed independently from the admin
            # bundle. Treat the bundle as an optional integration instead of
            # emitting a startup error for every WebProvider.
            return

        if admin_bundle and hasattr(admin_bundle, "mount_to_app"):
            await admin_bundle.mount_to_app(app, container)
