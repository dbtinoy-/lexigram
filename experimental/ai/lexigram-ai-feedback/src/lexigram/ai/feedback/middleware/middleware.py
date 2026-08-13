"""Feedback middleware for automatic feedback capture.

Integrates with Lexigram's middleware system to automatically capture
request/response data for feedback collection.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
import inspect
from typing import Any

from lexigram.ai.feedback.exceptions import FeedbackAuthorizationError
from lexigram.ai.feedback.processors.processor_registry import FeedbackProcessorRegistry
from lexigram.ai.feedback.services.collector import FeedbackCollector
from lexigram.ai.feedback.types import FeedbackType


@dataclass(frozen=True)
class FeedbackAuthContext:
    """Identity material handed to the middleware's authorization callback.

    Attributes:
        context_id: Feedback context ID the caller is submitting against.
        metadata: Remaining keyword arguments the host framework supplied
            to the endpoint handler (e.g. an authenticated user or request
            object). May be empty.
    """

    context_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


class FeedbackMiddleware:
    """Middleware for automatic feedback capture.

    Captures prediction inputs/outputs automatically and provides
    hooks for user feedback collection.

    When an :attr:`authorize` callback is supplied, feedback submissions
    via ``create_feedback_endpoint()`` are gated on it. Leaving it unset
    means the endpoint is open to anyone who can reach it — an explicit,
    informed choice, not an enforced control.

    Example:
        >>> from lexigram.app import Application
        >>> from lexigram.ai.feedback import FeedbackMiddleware, FeedbackCollector
        >>>
        >>> app = Application()
        >>> collector = FeedbackCollector()
        >>> middleware = FeedbackMiddleware(collector)
        >>> app.use(middleware)
    """

    def __init__(
        self,
        collector: FeedbackCollector,
        capture_inputs: bool = True,
        capture_outputs: bool = True,
        capture_metadata: bool = True,
        registry: FeedbackProcessorRegistry | None = None,
        authorize: Callable[[FeedbackAuthContext], bool | Awaitable[bool]]
        | None = None,
    ):
        """Initialize feedback middleware.

        Args:
            collector: Feedback collector instance
            capture_inputs: Whether to capture request inputs
            capture_outputs: Whether to capture response outputs
            capture_metadata: Whether to capture additional metadata
            registry: Feedback processor registry (defaults to one with built-in processors)
            authorize: Optional callback gating feedback submissions.
                Receives the submission's context id and metadata; return
                True to accept, False to raise
                :class:`~lexigram.ai.feedback.exceptions.FeedbackAuthorizationError`.
                Sync and async callables are supported. ``None`` (default)
                performs no check — the endpoint is open to anyone who can
                reach it.
        """
        self.collector = collector
        self.capture_inputs = capture_inputs
        self.capture_outputs = capture_outputs
        self.capture_metadata = capture_metadata
        self.authorize = authorize
        self._registry = (
            registry
            if registry is not None
            else FeedbackProcessorRegistry.with_defaults()
        )

    async def __call__(
        self,
        context: Any,  # Request context
        next_handler: Callable,
    ) -> Any:
        """Middleware handler.

        Args:
            context: Request context
            next_handler: Next middleware in chain

        Returns:
            Response
        """
        # Extract request data
        request_data = {}

        if self.capture_inputs:
            # Capture input data from context
            # This is framework-specific - adapt to actual context structure
            request_data["input"] = getattr(context, "body", None)

        if self.capture_metadata:
            # Capture metadata (user ID, session, etc.)
            request_data["user_id"] = getattr(context, "user_id", None)
            request_data["session_id"] = getattr(context, "session_id", None)
            request_data["endpoint"] = getattr(context, "path", None)

        # Call next handler
        response = await next_handler(context)

        # Capture output
        if self.capture_outputs:
            request_data["output"] = response

        # Store context for later feedback
        # In practice, you'd store this with a request ID
        # and allow users to provide feedback via API
        context_id = getattr(context, "request_id", "unknown")
        request_data["context_id"] = context_id

        # Store in context for access by feedback endpoints
        if hasattr(context, "set_metadata"):
            context.set_metadata("feedback_context", request_data)

        return response

    def create_feedback_endpoint(self) -> Callable:
        """Create a feedback submission endpoint.

        The returned handler first consults the middleware's
        ``authorize`` callback (if set); a denied submission raises
        :class:`~lexigram.ai.feedback.exceptions.FeedbackAuthorizationError`
        before any processing.

        Returns:
            Async handler function for feedback submission

        Example:
            >>> middleware = FeedbackMiddleware(collector)
            >>> feedback_handler = middleware.create_feedback_endpoint()
            >>> # Use with your web framework:
            >>> # app.post("/feedback", feedback_handler)
        """

        async def feedback_handler(
            context_id: str,
            feedback_type: str,
            value: Any,
            *,
            owner_id: str,
            **kwargs,
        ) -> dict[str, str]:
            """Handle feedback submission.

            Args:
                context_id: Context ID from original request.
                feedback_type: Type of feedback (rating, text, etc.).
                value: Feedback value.
                owner_id: Owner scope; the item is recorded under this owner.
                **kwargs: Additional metadata (passed to the authorize
                    callback as identity material).

            Returns:
                Response with feedback ID.

            Raises:
                FeedbackAuthorizationError: If the authorize callback is
                    set and denies the submission.
            """
            if self.authorize is not None:
                decision = self.authorize(
                    FeedbackAuthContext(context_id=context_id, metadata=dict(kwargs))
                )
                if inspect.isawaitable(decision):
                    decision = await decision
                if not decision:
                    raise FeedbackAuthorizationError(
                        f"caller not authorized to submit feedback for context {context_id}"
                    )

            fb_type = FeedbackType[feedback_type.upper()]
            context_dict = {"context_id": context_id, **kwargs}

            feedback_id = await self._registry.process(
                fb_type,
                value,
                context_dict,
                self.collector,
                owner_id=owner_id,
            )

            return {
                "status": "success",
                "feedback_id": feedback_id,
            }

        return feedback_handler

    def __repr__(self) -> str:
        """String representation."""
        return f"FeedbackMiddleware(collector={self.collector})"


class FeedbackContext:
    """Context manager for feedback collection during operations.

    Automatically captures context and results for feedback.

    Example:
        >>> collector = FeedbackCollector()
        >>> async with FeedbackContext(collector, operation="prediction") as ctx:
        ...     result = await model.predict(input_data)
        ...     ctx.set_result(result)
        >>> # Feedback context is automatically stored
    """

    def __init__(
        self,
        collector: FeedbackCollector,
        operation: str,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize feedback context.

        Args:
            collector: Feedback collector
            operation: Operation name
            metadata: Additional metadata
        """
        self.collector = collector
        self.operation = operation
        self.metadata = metadata or {}
        self._input: Any = None
        self._result: Any = None
        self._context_id: str | None = None

    def set_input(self, input_data: Any) -> None:
        """Set input data.

        Args:
            input_data: Input to the operation
        """
        self._input = input_data

    def set_result(self, result: Any) -> None:
        """Set operation result.

        Args:
            result: Result of the operation
        """
        self._result = result

    async def __aenter__(self) -> Any:
        """Enter context."""
        import uuid

        self._context_id = str(uuid.uuid4())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Any:
        """Exit context and store feedback context."""
        # Store context for later feedback
        context_data = {
            "context_id": self._context_id,
            "operation": self.operation,
            "input": self._input,
            "output": self._result,
            **self.metadata,
        }

        # In practice, you'd store this in a database or cache
        # for later feedback submission
        # For now, just pass - actual storage depends on integration

        if exc_type is not None:
            # Store error information
            context_data["error"] = str(exc_val)

    def __repr__(self) -> str:
        """String representation."""
        return f"FeedbackContext(operation={self.operation}, id={self._context_id})"
