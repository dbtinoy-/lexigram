"""Type definitions for Configuration Center."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.domain import DomainModel
from lexigram.validation import Field

__all__ = [
    "DEFAULT_CATEGORIES",
    "ConfigCategory",
    "get_default_categories",
]


@dataclass(init=False)
class ConfigCategory(DomainModel):
    """A grouping of configuration specs.

    Categories organize related configuration specs into logical groups
    displayed in the Configuration Center sidebar.

    Attributes:
        name: Internal identifier (e.g., "env", "app", "system")
        label: Display label (e.g., "Environment", "Application", "System")
        icon: Icon identifier for the category header
        order: Sort order for display (lower = higher priority)
        description: Optional description shown in the UI
    """

    name: str
    label: str
    icon: str = Field(default="folder")
    order: int = Field(default=100)
    description: str = Field(default="")

    # Populated dynamically from registry
    specs: list = Field(default_factory=list)


# Default category definitions
DEFAULT_CATEGORIES: tuple[ConfigCategory, ...] = (
    ConfigCategory(
        name="env",
        label="Environment",
        icon="server",
        order=10,
        description="Environment variables and runtime configuration",
    ),
    ConfigCategory(
        name="app",
        label="Application",
        icon="layout",
        order=20,
        description="Application-specific settings",
    ),
    ConfigCategory(
        name="system",
        label="System",
        icon="settings",
        order=30,
        description="Core system and admin interface settings",
    ),
)


def get_default_categories() -> list[ConfigCategory]:
    """Return a fresh copy of default categories."""
    return [
        ConfigCategory(
            name=c.name,
            label=c.label,
            icon=c.icon,
            order=c.order,
            description=c.description,
        )
        for c in DEFAULT_CATEGORIES
    ]
