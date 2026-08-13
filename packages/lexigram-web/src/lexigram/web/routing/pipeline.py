"""Web request execution pipeline.

Orchestrates the execution of guards, interceptors, and handlers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.web.interceptors.pipeline import InterceptorChain

if TYPE_CHECKING:
    from lexigram.contracts.web.guard import GuardProtocol
    from lexigram.contracts.web.protocols import ExceptionFilterProtocol
    from lexigram.web.filters.pipeline import FilterPipeline
    from lexigram.web.protocols import WebInterceptorProtocol
    from lexigram.web.routing.execution_context import WebExecutionContext
    from lexigram.web.serialization.serializers import ResponseSerializer


class RequestPipeline:
    """Orchestrates the request execution lifecycle."""

    def __init__(
        self,
        guards: list[GuardProtocol] | None = None,
        interceptors: list[WebInterceptorProtocol] | None = None,
        filters: list[ExceptionFilterProtocol] | None = None,
        fallback_pipeline: FilterPipeline | None = None,
        response_serializer: ResponseSerializer | None = None,
    ):
        """Initialize the pipeline.

        Args:
            guards: List of guards to execute.
            interceptors: List of interceptors to execute.
            filters: List of exception filters to execute.
            fallback_pipeline: Optional fallback pipeline (e.g. from the Router).
            response_serializer: Optional pre-wired ResponseSerializer instance.
        """
        self.guards = guards or []
        self.interceptors = interceptors or []
        self.filters = filters or []
        self.fallback_pipeline = fallback_pipeline
        self.response_serializer = response_serializer

    async def execute(self, context: WebExecutionContext) -> Any:
        """Execute the pipeline for the given context.

        Args:
            context: The execution context.

        Returns:
            The result of the handler (possibly transformed).
        """
        try:
            # 1. Execute Guards
            for guard in self.guards:
                if not await guard.can_activate(context):
                    from lexigram.web.exceptions import ForbiddenError

                    raise ForbiddenError("Access denied by guard")

            # 2. Execute Interceptors & Handler
            # We wrap the final handler call in a CallHandlerProtocol to be used by interceptors
            async def final_handler() -> Any:
                from lexigram.web.routing.parameter_binder import ParameterBinder

                # Resolve parameters using binder
                sig_info = context.route_metadata.get("sig_info")
                if not sig_info:
                    # Fallback to computing on the fly (less efficient)
                    import inspect

                    from lexigram.web.routing.validation import (
                        _cached_get_type_hints_for_handler,
                    )

                    sig = inspect.signature(context.handler)
                    hints = _cached_get_type_hints_for_handler(context.handler)
                    sig_info = {"sig": sig, "hints": hints}

                binder = ParameterBinder(sig_info["sig"], sig_info["hints"])
                kwargs = await binder.bind(context)

                return await context.handler(**kwargs)

            # Build interceptor chain
            chain = InterceptorChain(self.interceptors, 0, final_handler, context)
            result = await chain.handle()

            # 3. Post-execution: Serialize result to Response if needed
            from starlette.responses import Response as StarletteResponse

            if isinstance(result, StarletteResponse):
                return result

            from lexigram.web.serialization.serializers import ResponseSerializer

            route = context.route_metadata.get("route")
            serializer = self.response_serializer or ResponseSerializer()

            return await serializer.serialize(
                result,
                context.request,
                route=route,
            )

        except Exception as e:  # noqa: BLE001 — pipeline safety net; dispatches any error to registered exception filters
            # Match and execute appropriate filter
            # Local filters take precedence
            for f in reversed(self.filters):
                if f.can_handle(e):
                    return await f.handle(e, context.request)

            # Check for fallback pipeline (e.g. from the Router)
            if self.fallback_pipeline:
                return await self.fallback_pipeline.handle(e, context.request)

            # Check for truly global filters if no fallback handled it
            from lexigram.web.filters.pipeline import get_filter_pipeline

            global_pipeline = get_filter_pipeline(context.container)
            if global_pipeline and global_pipeline is not self.fallback_pipeline:
                return await global_pipeline.handle(e, context.request)

            # Re-raise if no filter found
            raise


__all__ = ["RequestPipeline"]
