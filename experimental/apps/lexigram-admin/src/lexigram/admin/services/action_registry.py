"""Action registry: types, protocols, and ActionRegistry for admin actions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.admin.exceptions import (
        AdminValidationError,
    )
    from lexigram.contracts.admin.action_hooks import ActionHookProtocol

T = TypeVar("T")


class ActionType(str, Enum):
    """Types of admin actions."""

    SINGLE = "single"  # Operates on a single resource
    BULK = "bulk"  # Operates on multiple resources
    GLOBAL = "global"  # Not tied to resources


class ActionExecutionMode(str, Enum):
    """How an action should be executed."""

    SYNC = "sync"  # Execute immediately
    ASYNC = "async"  # Execute as background task
    CONFIRM = "confirm"  # Require user confirmation first


@dataclass
class ActionConfig:
    """Configuration for an admin action."""

    name: str
    label: str
    description: str = ""
    icon: str | None = None

    # Action type
    action_type: ActionType = ActionType.SINGLE
    execution_mode: ActionExecutionMode = ActionExecutionMode.SYNC

    # Authorization
    permission: str | None = None

    # Confirmation
    confirm_message: str | None = None
    confirm_style: str = "warning"  # info, warning, danger

    # UI
    button_variant: str = "secondary"
    show_in_list: bool = True
    show_in_detail: bool = True

    # Bulk specific
    min_selection: int = 1
    max_selection: int | None = None

    # Form for action parameters
    has_form: bool = False
    form_schema: dict[str, Any] | None = None


@dataclass
class ActionContext:
    """Context for action execution."""

    user: Any
    resource_name: str
    action_name: str

    # Target(s)
    record_id: Any | None = None
    record_ids: list[Any] = field(default_factory=list)

    # Form data
    parameters: dict[str, Any] = field(default_factory=dict)

    # Additional context
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_bulk(self) -> bool:
        """Check if this is a bulk action."""
        return bool(
            len(self.record_ids) > 1 or (not self.record_id and self.record_ids)
        )

    @property
    def target_count(self) -> int:
        """Get the number of target records."""
        if self.record_ids:
            return len(self.record_ids)
        return 1 if self.record_id else 0


@dataclass
class ActionResult:
    """Result of a successful action execution."""

    message: str
    data: Any = None

    # For bulk actions
    successful_count: int = 0
    failed_count: int = 0
    failures: list[tuple[Any, str]] = field(default_factory=list)  # (id, error_msg)

    # For async actions
    task_id: str | None = None

    # Redirect
    redirect_url: str | None = None

    # Refresh target
    refresh_target: str | None = None

    @classmethod
    def bulk(
        cls,
        message: str,
        successful_count: int,
        failed_count: int,
        failures: list[tuple[Any, str]] | None = None,
    ) -> ActionResult:
        """Create a bulk action result."""
        return cls(
            message=message,
            successful_count=successful_count,
            failed_count=failed_count,
            failures=failures or [],
        )

    @classmethod
    def async_started(
        cls,
        task_id: str,
        message: str = "Action started",
    ) -> ActionResult:
        """Create an async action started result."""
        return cls(
            message=message,
            task_id=task_id,
        )


@runtime_checkable
class ActionHandler(Protocol):
    """Protocol for action handlers."""

    async def execute(self, context: ActionContext) -> ActionResult: ...


@runtime_checkable
class ActionValidator(Protocol):
    """Protocol for action validators."""

    async def validate(
        self,
        context: ActionContext,
        config: ActionConfig,
    ) -> Result[None, AdminValidationError]: ...


class AbstractActionHandler(ABC):
    """Base class for action handlers."""

    def __init__(self) -> None:
        """Initialize lifecycle hook collections."""
        self.before_hooks: list[ActionHookProtocol] = []
        self.after_hooks: list[ActionHookProtocol] = []
        self.failure_hooks: list[ActionHookProtocol] = []

    def register_hooks(
        self,
        *,
        before: list[ActionHookProtocol] | None = None,
        after: list[ActionHookProtocol] | None = None,
        failure: list[ActionHookProtocol] | None = None,
    ) -> None:
        """Register lifecycle hooks on this handler.

        Args:
            before: Hooks run before the action body.
            after: Hooks run after successful execution.
            failure: Hooks run when the action fails.
        """
        if before:
            self.before_hooks.extend(before)
        if after:
            self.after_hooks.extend(after)
        if failure:
            self.failure_hooks.extend(failure)

    @abstractmethod
    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute the action."""
        ...

    async def validate(
        self,
        context: ActionContext,
        config: ActionConfig,
    ) -> Result[None, AdminValidationError]:
        """Validate action parameters. Override for custom validation."""
        return Ok(None)

    async def on_success(self, context: ActionContext, result: ActionResult) -> None:
        """Called after successful execution. Override for post-processing."""

    async def on_failure(self, context: ActionContext, error: Exception) -> None:
        """Called after failed execution. Override for error handling."""


class FunctionActionHandler(AbstractActionHandler):
    """Action handler that wraps a function."""

    def __init__(
        self,
        func: Callable[[ActionContext], Any],
        is_async: bool = True,
    ):
        super().__init__()
        self.func = func
        self.is_async = is_async

    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute the wrapped function."""
        if self.is_async:
            result = await self.func(context)
        else:
            result = self.func(context)

        if isinstance(result, ActionResult):
            return result

        return ActionResult(message="Action completed", data=result)


class ActionRegistry:
    """Registry for admin actions."""

    def __init__(self) -> None:
        self._actions: dict[str, dict[str, tuple[ActionConfig, ActionHandler]]] = {}
        # resource_name -> action_name -> (config, handler)

        self._global_actions: dict[str, tuple[ActionConfig, ActionHandler]] = {}

    def register(
        self,
        resource_name: str,
        config: ActionConfig,
        handler: ActionHandler | Callable[[ActionContext], Any],
    ) -> None:
        """Register an action for a resource.

        Args:
            resource_name: Resource this action applies to
            config: Action configuration
            handler: Action handler or callable
        """
        if resource_name not in self._actions:
            self._actions[resource_name] = {}

        if callable(handler) and not isinstance(handler, ActionHandler):
            handler = FunctionActionHandler(handler)

        self._actions[resource_name][config.name] = (config, handler)

    def register_global(
        self,
        config: ActionConfig,
        handler: ActionHandler | Callable[[ActionContext], Any],
    ) -> None:
        """Register a global action (not tied to a resource).

        Args:
            config: Action configuration
            handler: Action handler or callable
        """
        if callable(handler) and not isinstance(handler, ActionHandler):
            handler = FunctionActionHandler(handler)

        self._global_actions[config.name] = (config, handler)

    def get(
        self,
        resource_name: str,
        action_name: str,
    ) -> tuple[ActionConfig, ActionHandler] | None:
        """Get an action by resource and name."""
        if resource_name in self._actions:
            return self._actions[resource_name].get(action_name)
        return None

    def get_global(self, action_name: str) -> tuple[ActionConfig, ActionHandler] | None:
        """Get a global action by name."""
        return self._global_actions.get(action_name)

    def get_actions_for_resource(
        self,
        resource_name: str,
        action_type: ActionType | None = None,
    ) -> list[ActionConfig]:
        """Get all actions for a resource.

        Args:
            resource_name: Resource name
            action_type: Optional filter by action type

        Returns:
            List of action configurations
        """
        if resource_name not in self._actions:
            return []

        configs = [x[0] for x in self._actions[resource_name].values()]

        if action_type:
            configs = list(filter(lambda c: c.action_type == action_type, configs))

        return configs

    def get_all_global_actions(self) -> list[ActionConfig]:
        """Get all global actions."""
        return [x[0] for x in self._global_actions.values()]


__all__ = [
    "AbstractActionHandler",
    "ActionConfig",
    "ActionContext",
    "ActionExecutionMode",
    "ActionHandler",
    "ActionRegistry",
    "ActionResult",
    "ActionType",
    "ActionValidator",
    "FunctionActionHandler",
]
