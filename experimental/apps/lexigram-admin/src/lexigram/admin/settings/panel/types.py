"""Type definitions for Configuration Center."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.domain import DomainModel
from lexigram.validation import Field

__all__ = [
    "ConfigCategory",
    "PanelLink",
]


@dataclass(frozen=True, slots=True)
class PanelLink:
    """Sidebar link to a contributor-owned settings panel (R50, doc 46).

    Contributor panels (``SettingsPanelDefinition``) are self-owned pages
    on their own routes, not ConfigRegistry specs — this is the plain
    presentation shape the sidebar renders so the layout holds data, not
    live handler references.

    Attributes:
        title: Display label.
        url: Absolute panel route (e.g. ``/admin/system/info``).
        icon: Icon identifier for the link.
        category: Sidebar group label (e.g. ``System``).
    """

    title: str
    url: str
    icon: str = "file-text"
    category: str = "Tools"


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
