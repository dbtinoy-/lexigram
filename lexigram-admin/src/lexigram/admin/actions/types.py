"""Action types for lexigram-admin actions module.

Defines shared enums, dataclasses, and value objects used across
the action system. All types here are framework-level and can be
imported by any admin action implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionColor(str, Enum):
    """Visual color variants for action buttons and indicators."""

    GRAY = "gray"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"
    INFO = "info"


@dataclass
class ActionContext:
    """Contextual information passed to action execution.

    Carries the request, authenticated user, resource name,
    authorizer, audit writer, and request-metadata fields
    that together describe the environment in which an action runs.
    """

    request: Any | None = None
    user: Any | None = None
    resource_name: str = ""
    resource_prefix: str = ""
    authorizer: Any | None = None
    audit_writer: Any | None = None
    correlation_id: str | None = None
    request_id: str | None = None
    request_ip: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    record_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class ConfirmationConfig:
    """Configuration for action confirmation dialogs.

    Attributes:
        title: Required dialog title.
        message: Optional explanatory body text.
        style: Visual style of the confirmation. Defaults to WARNING.
    """

    title: str
    message: str | None = None
    style: ActionColor = ActionColor.WARNING


__all__ = [
    "ActionColor",
    "ActionContext",
    "ConfirmationConfig",
]
