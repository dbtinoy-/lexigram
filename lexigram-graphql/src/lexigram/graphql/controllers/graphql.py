"""GraphQL Controller for lexigram-web integration.

This module provides a Controller-based implementation for GraphQL endpoints,
following the lexigram-contracts.web.Controller pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.responses import JSONResponse

from lexigram.contracts.web import post
from lexigram.contracts.web.controller import ControllerProtocol
from lexigram.graphql import constants as const
from lexigram.graphql.exceptions import AuthenticationError
from lexigram.logging import get_logger

if TYPE_CHECKING:
    # GraphQLExecutorProtocol imported by providers/tests; not needed here now
    from lexigram.contracts.core.di import ContainerProtocol
    from lexigram.contracts.graphql import GraphQLRequestProtocol
    from lexigram.graphql.di.provider import GraphQLProvider

logger = get_logger(__name__)


class GraphQLController(ControllerProtocol):
    """GraphQL HTTP endpoint controller.

    This controller exposes GraphQL queries and mutations via HTTP POST
    at the configured path (default: ``/graphql``).

    Example:
        Registration is handled automatically by the GraphQL provider.
        To mount the controller manually, resolve the web application via the
        ``HTTPApplicationProtocol`` from contracts — do not import from
        ``lexigram.web`` directly::

            from lexigram.contracts.web.protocols import HTTPApplicationProtocol
            # app = await container.resolve(HTTPApplicationProtocol)
            # app.mount("/graphql", graphql_view)
    """

    container: ContainerProtocol | None = None

    def __init__(self, provider: GraphQLProvider | None = None) -> None:
        """Initialize the GraphQL controller.

        Args:
            provider: GraphQL provider instance. If None, will be resolved
                     from the DI container at request time.
        """
        self._provider = provider

    @classmethod
    def collect_routes(cls) -> list[dict[str, Any]]:
        """Collect routes from controller methods."""
        routes = []
        seen_handlers = set()

        for klass in cls.__mro__:
            if klass is object:
                continue

            for attr_name in dir(klass):
                if attr_name.startswith("_") or attr_name in seen_handlers:
                    continue

                attr_value = getattr(klass, attr_name, None)
                if attr_value is not None and hasattr(attr_value, "_route_config"):
                    route_config = attr_value._route_config
                    routes.append(
                        {
                            "method": route_config["method"],
                            "path": route_config["path"],
                            "handler_name": attr_name,
                            "response_model": route_config.get("response_model"),
                            "request_model": route_config.get("request_model"),
                            "status_code": route_config.get("status_code", 200),
                            "summary": route_config.get("summary"),
                            "description": route_config.get("description"),
                            "tags": route_config.get("tags"),
                            "operation_id": route_config.get("operation_id"),
                            "responses": route_config.get("responses"),
                            "deprecated": route_config.get("deprecated", False),
                        }
                    )
                    seen_handlers.add(attr_name)

        return routes

    @post(const.DEFAULT_GRAPHQL_PATH)
    async def execute(self, request: GraphQLRequestProtocol) -> JSONResponse:
        """Execute a GraphQL query.

        Args:
            request: HTTP request containing the GraphQL query.

        Returns:
            JSON response with query results or errors.
        """
        provider = self._get_provider(request)
        executor = provider.executor() if provider else None

        if not provider or not executor:
            return JSONResponse(
                {"errors": [{"message": "GraphQL subsystem not configured"}]},
                status_code=503,
            )

        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            return JSONResponse(
                {"errors": [{"message": "Invalid JSON body"}]},
                status_code=400,
            )

        query = body.get("query")
        if not query:
            return JSONResponse(
                {"errors": [{"message": "No query provided"}]},
                status_code=400,
            )

        try:
            # Extract user from request state or scope extensions
            user = getattr(request.state, "user", None)
            if user is None:
                user = request.scope.get("extensions", {}).get("user")

            context = (
                await provider.context_factory.create_context(
                    raw_request=request,
                    user=user,
                    metadata={"container": getattr(self, "container", None)},
                )
                if provider.context_factory is not None
                else None
            )

            result = await executor.execute(
                query,
                variables=body.get("variables"),
                operation_name=body.get("operationName"),
                context=context,
            )

            if result.is_err():
                error = result.unwrap_err()
                logger.error("GraphQL setup error: %s", error)
                return JSONResponse(
                    {"errors": [{"message": f"Transport error: {error!s}"}]},
                    status_code=500,
                )

            gql_response = result.unwrap()
            response_data: dict[str, Any] = {"data": gql_response.data}
            if gql_response.errors:
                response_data["errors"] = [
                    {"message": str(e)} for e in gql_response.errors
                ]

            return JSONResponse(response_data)

        except AuthenticationError as exc:
            logger.warning("auth_required", error=str(exc))
            return JSONResponse(
                {
                    "data": None,
                    "errors": [
                        {
                            "message": str(exc),
                            "extensions": {"code": "AUTH_REQUIRED"},
                        }
                    ],
                },
            )
        except Exception as exc:  # noqa: BLE001 — controller boundary; all errors become HTTP 500 GraphQL error responses
            logger.exception("GraphQL execution error")
            return JSONResponse(
                {"errors": [{"message": f"Execution error: {exc}"}]},
                status_code=500,
            )

    def _get_provider(self, request: GraphQLRequestProtocol) -> GraphQLProvider | None:
        """Get GraphQL provider from request app or instance.

        Args:
            request: Current HTTP request.

        Returns:
            GraphQL provider or None if not available.
        """
        # Use injected provider if available
        if self._provider is not None:
            return self._provider

        # Try to get from request app
        app = getattr(request, "app", None)
        if app is not None:
            provider: GraphQLProvider | None = getattr(
                app, "graphql_provider", lambda: None
            )()
            if provider is not None and not hasattr(provider, "_mock_return_value"):
                return provider

        return None


class GraphQLSubscriptionController(ControllerProtocol):
    """GraphQL WebSocket subscription controller.

    This controller handles GraphQL subscriptions via WebSocket
    at the configured path (default: ``/graphql/subscriptions``).
    """

    def __init__(self, provider: GraphQLProvider | None = None) -> None:
        """Initialize the subscription controller.

        Args:
            provider: GraphQL provider instance. If None, will be resolved
                     from the DI container at request time.
        """
        self._provider = provider

    @classmethod
    def collect_routes(cls) -> list[dict[str, Any]]:
        """Collect routes from controller methods."""
        return []

    # Note: WebSocket routes use a different mechanism than HTTP.
    # This controller serves as a placeholder for WebSocket handler integration.
    # The actual WebSocket handling is done via GraphQLWSHandler in subscriptions.


__all__ = ["GraphQLController", "GraphQLSubscriptionController"]
