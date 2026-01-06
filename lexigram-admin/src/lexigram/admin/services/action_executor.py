"""ActionExecutor for executing custom admin actions with validation and authorization.

See action_registry for types, protocols, and ActionRegistry.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from lexigram.admin.exceptions import (
    AdminError,
    AdminValidationError,
    PermissionDeniedError,
)
from lexigram.admin.services.action_registry import (
    ActionConfig,
    ActionContext,
    ActionExecutionMode,
    ActionHandler,
    ActionRegistry,
    ActionResult,
    ActionType,
)
from lexigram.contracts.admin.authorizer import AdminAuthorizerProtocol
from lexigram.di.decorators import inject
from lexigram.result import Err, Ok, Result


@runtime_checkable
class TaskScheduler(Protocol):
    """Protocol for scheduling background tasks."""

    async def schedule(
        self,
        task_name: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> str: ...


@inject
class ActionExecutor:
    """Executes admin actions with validation and authorization.

    Handles:
    - Action lookup and validation
    - Authorization checks
    - Sync and async execution
    - Result handling
    - Real-time notification publishing via AdminEventHub

    Example:
        >>> executor = ActionExecutor(registry, authorizer)
        >>> context = ActionContext(
        ...     user=current_user,
        ...     resource_name="users",
        ...     action_name="deactivate",
        ...     record_id=123,
        ... )
        >>> result = await executor.execute(context)
    """

    def __init__(
        self,
        registry: ActionRegistry,
        authorizer: AdminAuthorizerProtocol | None = None,
        task_scheduler: TaskScheduler | None = None,
        event_hub: Any | None = None,
    ):
        """Initialize the action executor.

        Args:
            registry: Action registry
            authorizer: Optional authorizer for permission checks
            task_scheduler: Optional task scheduler for async actions
            event_hub: Optional AdminEventHub for publishing real-time notifications
        """
        self.registry = registry
        self.authorizer = authorizer
        self.task_scheduler = task_scheduler
        self.event_hub = event_hub

    async def execute(
        self,
        context: ActionContext,
    ) -> Result[
        ActionResult, PermissionDeniedError | AdminValidationError | AdminError
    ]:
        """Execute an action.

        Args:
            context: Action execution context

        Returns:
            Result containing ActionResult or error
        """
        # Get action
        action = self.registry.get(context.resource_name, context.action_name)
        if not action:
            action = self.registry.get_global(context.action_name)

        if not action:
            return Err(
                AdminError(
                    message=f"Action '{context.action_name}' not found for resource '{context.resource_name}'",
                ),
            )

        config, handler = action

        # Authorization
        if self.authorizer and config.permission:
            can_execute = await self.authorizer.can_execute_action(
                context.user,
                context.resource_name,
                context.action_name,
            )
            if not can_execute:
                return Err(
                    PermissionDeniedError(
                        resource=context.resource_name,
                        action=context.action_name,
                        message=f"No permission to execute '{context.action_name}'",
                    ),
                )

        # Validate bulk constraints
        if config.action_type == ActionType.BULK:
            if context.target_count < config.min_selection:
                return Err(
                    AdminValidationError(
                        message=f"Select at least {config.min_selection} item(s)",
                        errors={  # type: ignore[arg-type]
                            "selection": [
                                f"Minimum {config.min_selection} items required",
                            ],
                        },
                    ),
                )
            if config.max_selection and context.target_count > config.max_selection:
                return Err(
                    AdminValidationError(
                        message=f"Cannot select more than {config.max_selection} items",
                        errors={  # type: ignore[arg-type]
                            "selection": [
                                f"Maximum {config.max_selection} items allowed",
                            ],
                        },
                    ),
                )

        # Custom validation
        if hasattr(handler, "validate"):
            validation_result = await handler.validate(context, config)
            if validation_result.is_err():
                return validation_result

        # Execute based on mode
        try:
            if config.execution_mode == ActionExecutionMode.ASYNC:
                return await self._execute(context, config, handler)  # type: ignore[return-value]
            result: Result[ActionResult, AdminError] = await self._execute_direct(
                context, handler
            )
            await self._publish_action_notification(context, config, result)
            return result  # type: ignore[return-value]
        except (RuntimeError, ValueError, TypeError, OSError) as e:
            if hasattr(handler, "on_failure"):
                await handler.on_failure(context, e)
            await self._publish_action_failure(
                context, config.label or context.action_name, str(e)
            )
            return Err(
                AdminError(
                    message=str(e),
                ),
            )

    async def _execute_direct(
        self,
        context: ActionContext,
        handler: ActionHandler,
    ) -> Result[ActionResult, AdminError]:
        """Execute action directly (sync mode, but async handler)."""
        result = await handler.execute(context)

        if hasattr(handler, "on_success"):
            await handler.on_success(context, result)

        return Ok(result)

    async def _execute(
        self,
        context: ActionContext,
        config: ActionConfig,
        handler: ActionHandler,
    ) -> Result[ActionResult, AdminError]:
        """Execute action asynchronously via task queue."""
        if not self.task_scheduler:
            # Fallback to direct execution
            return await self._execute_direct(context, handler)

        # Schedule task
        task_id = await self.task_scheduler.schedule(
            f"admin.action.{context.resource_name}.{context.action_name}",
            args=(context,),
            kwargs={},
        )

        return Ok(
            ActionResult.async_started(
                task_id=task_id,
                message=f"Action '{config.label}' has been scheduled",
            ),
        )

    async def _publish_action_notification(
        self,
        context: ActionContext,
        config: ActionConfig,
        result: Result[ActionResult, AdminError],
    ) -> None:
        """Publish a notification event for a completed action."""
        if not self.event_hub:
            return
        if result.is_ok():
            action_result = result.unwrap()
            await self.event_hub.publish_notification(
                title=f"Action completed: {config.label or context.action_name}",
                message=action_result.message[:200]
                if action_result.message
                else f"Action '{context.action_name}' succeeded",
                level="success",
                target_users=[getattr(context.user, "id", None)]
                if context.user
                else None,
            )

    async def _publish_action_failure(
        self,
        context: ActionContext,
        action_label: str,
        error: str,
    ) -> None:
        """Publish a notification event for a failed action."""
        if not self.event_hub:
            return
        await self.event_hub.publish_notification(
            title=f"Action failed: {action_label}",
            message=error[:200],
            level="error",
            target_users=[getattr(context.user, "id", None)] if context.user else None,
        )

    def get_available_actions(
        self,
        resource_name: str,
        user_permissions: set[str] | None = None,
        context: str = "list",  # list, detail
    ) -> list[ActionConfig]:
        """Get actions available for a resource.

        Args:
            resource_name: Resource name
            user_permissions: Optional permissions to filter by
            context: Where actions will be shown (list or detail)

        Returns:
            List of available action configurations
        """
        actions = self.registry.get_actions_for_resource(resource_name)

        # Filter by context
        if context == "list":
            actions = list(filter(lambda a: a.show_in_list, actions))
        elif context == "detail":
            actions = list(filter(lambda a: a.show_in_detail, actions))

        # Filter by permissions
        if user_permissions:
            actions = [
                a
                for a in actions
                if not a.permission or a.permission in user_permissions
            ]

        return actions


# Decorator for registering actions


def action(
    name: str,
    label: str,
    *,
    resource: str | None = None,
    action_type: ActionType = ActionType.SINGLE,
    execution_mode: ActionExecutionMode = ActionExecutionMode.SYNC,
    permission: str | None = None,
    confirm_message: str | None = None,
    icon: str | None = None,
    **kwargs: Any,
) -> Callable[[Callable[[ActionContext], Any]], Callable[[ActionContext], Any]]:
    """Decorator to register an action handler.

    Example:
        @action("deactivate", "Deactivate User", resource="users", confirm_message="Deactivate this user?")
        async def deactivate_user(context: ActionContext) -> ActionResult:
            # implementation
            return ActionResult(message="User deactivated")
    """

    def decorator(
        func: Callable[[ActionContext], Any],
    ) -> Callable[[ActionContext], Any]:
        # Store action metadata on the function
        func._action_config = ActionConfig(  # type: ignore[attr-defined]
            name=name,
            label=label,
            action_type=action_type,
            execution_mode=execution_mode,
            permission=permission,
            confirm_message=confirm_message,
            icon=icon,
            **kwargs,
        )
        func._action_resource = resource  # type: ignore[attr-defined]
        return func

    return decorator


__all__ = [
    "AbstractActionHandler",
    "ActionConfig",
    "ActionContext",
    "ActionExecutionMode",
    "ActionExecutor",
    "ActionHandler",
    "ActionRegistry",
    "ActionResult",
    "ActionType",
    "ActionValidator",
    "FunctionActionHandler",
    "action",
]
