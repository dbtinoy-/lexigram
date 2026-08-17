"""Admin action definitions and dispatch for the relay gateway.

Holds the permissioned control-action surface (channel state, stream
cancellation, durable-channel CRUD) and the handler-loading and
dispatch helpers the contributor wires at boot.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib import import_module
from typing import Any

from lexigram.ai.relay.gateway.operations.controls import (
    PERMISSION_CHANNEL_CONTROL,
    PERMISSION_CHANNEL_MANAGE,
    PERMISSION_STREAM_CONTROL,
)
from lexigram.contracts.admin.types import (
    ActionParameterField,
    ActionParameterSchema,
    AdminActionDefinition,
)

__all__ = ["ACTIONS", "execute_action", "load_action_handlers"]

ACTIONS: tuple[AdminActionDefinition, ...] = (
    AdminActionDefinition(
        name="set_channel_state",
        title="Set Channel State",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:set_channel_state",
        icon="toggle-right",
        confirmation_message="Enable or drain this channel for new requests?",
        category="operations",
        permission=PERMISSION_CHANNEL_CONTROL,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="channel",
                    type_hint="str",
                    required=True,
                    description="Channel name from the gateway channel table.",
                ),
                ActionParameterField(
                    name="enabled",
                    type_hint="bool",
                    required=True,
                    description="Whether the channel accepts new requests.",
                ),
            ),
            description="Enable or drain a gateway channel.",
        ),
    ),
    AdminActionDefinition(
        name="force_cancel_stream",
        title="Force Cancel Stream",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:force_cancel_stream",
        icon="x-circle",
        confirmation_message="This terminates the upstream request immediately.",
        destructive=True,
        category="operations",
        permission=PERMISSION_STREAM_CONTROL,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="stream_id",
                    type_hint="str",
                    required=True,
                    description="Identifier of the stream session to cancel.",
                ),
            ),
        ),
    ),
    AdminActionDefinition(
        name="create_channel",
        title="Create Channel",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:create_channel",
        icon="plus-circle",
        confirmation_message="Create a durable relay channel?",
        category="operations",
        permission=PERMISSION_CHANNEL_MANAGE,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="name",
                    type_hint="str",
                    required=True,
                    description="Unique channel name.",
                ),
                ActionParameterField(
                    name="upstream_base_url",
                    type_hint="str",
                    required=True,
                    description="Upstream endpoint base URL.",
                ),
                ActionParameterField(
                    name="target_format",
                    type_hint="str",
                    required=True,
                    description=(
                        "Wire format: openai_chat, openai_responses, claude, or gemini."
                    ),
                ),
                ActionParameterField(
                    name="models",
                    type_hint="str",
                    required=True,
                    description="Comma-separated model aliases.",
                ),
                ActionParameterField(
                    name="priority",
                    type_hint="int",
                    required=False,
                    default=100,
                    description="Selection priority (lower routes first).",
                ),
                ActionParameterField(
                    name="weight",
                    type_hint="int",
                    required=False,
                    default=100,
                    description="Load-balancing weight.",
                ),
                ActionParameterField(
                    name="enabled",
                    type_hint="bool",
                    required=False,
                    default=True,
                    description="Whether the channel accepts new requests.",
                ),
                ActionParameterField(
                    name="timeout_seconds",
                    type_hint="float",
                    required=False,
                    default=60.0,
                    description="Upstream timeout in seconds.",
                ),
            ),
            description="Create a durable gateway channel.",
        ),
    ),
    AdminActionDefinition(
        name="update_channel",
        title="Update Channel",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:update_channel",
        icon="pencil",
        confirmation_message="Update this durable channel at the given revision?",
        category="operations",
        permission=PERMISSION_CHANNEL_MANAGE,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="name",
                    type_hint="str",
                    required=True,
                    description="Channel name to update.",
                ),
                ActionParameterField(
                    name="expected_revision",
                    type_hint="int",
                    required=True,
                    description="Revision the caller observed; stale writes are rejected.",
                ),
                ActionParameterField(
                    name="upstream_base_url",
                    type_hint="str",
                    required=True,
                    description="Upstream endpoint base URL.",
                ),
                ActionParameterField(
                    name="target_format",
                    type_hint="str",
                    required=True,
                    description="Wire format: openai_chat, openai_responses, claude, or gemini.",
                ),
                ActionParameterField(
                    name="models",
                    type_hint="str",
                    required=True,
                    description="Comma-separated model aliases.",
                ),
                ActionParameterField(
                    name="priority",
                    type_hint="int",
                    required=False,
                    default=100,
                    description="Selection priority (lower routes first).",
                ),
                ActionParameterField(
                    name="weight",
                    type_hint="int",
                    required=False,
                    default=100,
                    description="Load-balancing weight.",
                ),
                ActionParameterField(
                    name="enabled",
                    type_hint="bool",
                    required=False,
                    default=True,
                    description="Whether the channel accepts new requests.",
                ),
                ActionParameterField(
                    name="timeout_seconds",
                    type_hint="float",
                    required=False,
                    default=60.0,
                    description="Upstream timeout in seconds.",
                ),
            ),
            description="Update a durable gateway channel under compare-and-set.",
        ),
    ),
    AdminActionDefinition(
        name="delete_channel",
        title="Delete Channel",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:delete_channel",
        icon="trash-2",
        confirmation_message="Delete this channel permanently?",
        destructive=True,
        category="operations",
        permission=PERMISSION_CHANNEL_MANAGE,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="name",
                    type_hint="str",
                    required=True,
                    description="Channel name to delete.",
                ),
                ActionParameterField(
                    name="expected_revision",
                    type_hint="int",
                    required=True,
                    description="Revision the caller observed; stale deletes are rejected.",
                ),
            ),
            description="Delete a durable gateway channel under compare-and-set.",
        ),
    ),
    AdminActionDefinition(
        name="test_channel",
        title="Test Channel",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:test_channel",
        icon="activity",
        confirmation_message="Probe this channel through the health service?",
        category="operations",
        permission=PERMISSION_CHANNEL_MANAGE,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="name",
                    type_hint="str",
                    required=True,
                    description="Channel name to probe.",
                ),
            ),
            description="Run the channel health probe and report the verdict.",
        ),
    ),
)


def load_action_handlers(
    actions: Sequence[AdminActionDefinition],
) -> dict[str, Any]:
    """Import the handler callable for each action definition.

    Args:
        actions: Action definitions to resolve handlers for.

    Returns:
        Mapping of action name to its imported handler callable.
    """
    handlers: dict[str, Any] = {}
    for action in actions:
        module_path, _, handler_name = action.handler.partition(":")
        module = import_module(module_path)
        handlers[action.name] = getattr(module, handler_name)
    return handlers


async def execute_action(
    handlers: dict[str, Any],
    container: Any,
    action_name: str,
    params: dict[str, object],
) -> object:
    """Dispatch an action to its boot-resolved handler.

    Handlers run with the container captured at boot; a container is
    required.  Every handler performs server-side parameter validation
    before invoking the control service.

    Args:
        handlers: Action-name to handler callable mapping.
        container: The DI container captured at contributor boot.
        action_name: Name of the action to execute.
        params: Parameters forwarded to the action handler.

    Returns:
        The handler's result mapping.

    Raises:
        LookupError: Unknown action name.
        RuntimeError: Contributor booted without a container.
    """
    handler = handlers.get(action_name)
    if handler is None:
        raise LookupError(f"unknown relay-gateway action {action_name!r}")
    if container is None:
        raise RuntimeError("contributor has no container; on_admin_boot required")
    return await handler(container, **params)
