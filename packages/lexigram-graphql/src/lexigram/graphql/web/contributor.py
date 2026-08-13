"""GraphQL web contributor for controller and middleware discovery."""

from __future__ import annotations

from typing import Any


class GraphQLWebContributor:
    """Web contributor that registers GraphQL HTTP controller.

    This contributor exposes the GraphQL HTTP endpoint controller to the
    web provider via entry-point discovery. WebSocket subscriptions are
    handled separately by GraphQLIntegration.

    Example:
        Registered via entry-point in pyproject.toml::

            [project.entry-points."lexigram.web.contributors"]
            graphql = "lexigram.graphql.web.contributor:GraphQLWebContributor"
    """

    @property
    def contributor_id(self) -> str:
        """Return unique contributor identifier.

        Returns:
            The string "graphql" as the contributor identifier.
        """
        return "graphql"

    def get_controllers(self) -> list[type[Any]]:
        """Return GraphQL HTTP controller class.

        Returns:
            List containing GraphQLController class.
        """
        from lexigram.graphql.controllers.graphql import GraphQLController

        return [GraphQLController]

    def get_middleware(self) -> list[type[Any]]:
        """Return middleware classes contributed by GraphQL package.

        Currently GraphQL does not contribute any middleware.

        Returns:
            Empty list.
        """
        return []

    async def mount_to_app(self, app: Any, container: object) -> None:
        """No-op mount hook for GraphQL contributor.

        GraphQL exposes routes via controller rather than app mount.
        WebSocket subscriptions are handled separately by GraphQLIntegration.

        Args:
            app: The ASGI application (unused).
            container: The DI container (unused).
        """
