"""Feature flags and contributor configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False)
class AdminFeaturesConfig(DomainModel):
    """Feature flags for admin functionality."""

    # UI Features
    command_palette: bool = Field(default=True)
    keyboard_shortcuts: bool = Field(default=True)
    theme_toggle: bool = Field(default=True)
    search: bool = Field(default=True)

    # UX Features
    optimistic_updates: bool = Field(default=True)
    undo_redo: bool = Field(default=True)
    autosave: bool = Field(default=False)

    # Advanced Features
    audit_logging: bool = Field(default=True)
    activity_feed: bool = Field(default=False)
    notifications: bool = Field(default=True)
    webhooks: bool = Field(default=False)
    api_docs: bool = Field(default=True)

    model_config = {"extra": "allow"}


@dataclass(init=False)
class ContributorConfig(DomainModel):
    """Per-contributor enable/disable and options."""

    enabled: bool = Field(default=True)
    options: dict[str, Any] = Field(default_factory=dict)


@dataclass(init=False)
class FrameworkPagesConfig(DomainModel):
    """Framework management pages configuration."""

    enabled: bool = Field(default=True)
    require_permission: str = Field(default="admin:framework:access")
