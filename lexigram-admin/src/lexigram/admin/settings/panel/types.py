"""Type definitions for Configuration Center."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.domain import DomainModel
from lexigram.validation import Field

__all__ = [
    "ConfigCategory",
]


@dataclass(init=False)
class ConfigCategory(DomainModel):
    """A grouping of configuration specs.

    Categories organize related configuration specs into logical groups
    displayed in the Configuration Center sidebar. One category is built
    per distinct ``ConfigSpec.package_source`` registered with the
    ``ConfigRegistry`` — see ``SettingsController._build_categories``.

    Attributes:
        name: Internal identifier — the spec's package_source.
        label: Display label shown in the sidebar.
        icon: Icon identifier for the category header.
        order: Sort order for display (lower = higher priority).
        description: Optional description shown in the UI.
    """

    name: str
    label: str
    icon: str = Field(default="folder")
    order: int = Field(default=100)
    description: str = Field(default="")

    # Populated dynamically from registry
    specs: list = Field(default_factory=list)