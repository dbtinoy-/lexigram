"""Resource metadata value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class ResourceMeta:
    """Metadata for a resource."""

    name: str
    label: str
    label_plural: str
    icon: str | None = None

    # URLs
    prefix: str = ""

    # Default settings
    per_page: int = 20
    searchable_fields: list[str] | None = None
    default_sort: str = "id"
    default_sort_order: str = "desc"

    # Features
    enable_create: bool = True
    enable_edit: bool = True
    enable_delete: bool = True
    enable_clone: bool = True
    enable_bulk_actions: bool = True
    enable_export: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResourceMeta:
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            label=data.get("label", ""),
            label_plural=data.get("label_plural", ""),
            icon=data.get("icon"),
            prefix=data.get("prefix", ""),
            per_page=data.get("per_page", 20),
            searchable_fields=data.get("searchable_fields"),
            default_sort=data.get("default_sort", "id"),
            default_sort_order=data.get("default_sort_order", "desc"),
            enable_create=data.get("enable_create", True),
            enable_edit=data.get("enable_edit", True),
            enable_delete=data.get("enable_delete", True),
            enable_clone=data.get("enable_clone", True),
            enable_bulk_actions=data.get("enable_bulk_actions", True),
            enable_export=data.get("enable_export", True),
        )
