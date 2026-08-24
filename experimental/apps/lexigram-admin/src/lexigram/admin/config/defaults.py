"""Resource, table, form, and navigation default configurations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False)
class ResourceDefaults(DomainModel):
    """Default configuration for all resources."""

    per_page: int = Field(default=20, ge=1, le=1000)
    enable_search: bool = Field(default=True)
    enable_export: bool = Field(default=True)
    enable_bulk_actions: bool = Field(default=True)
    action_layout: Literal["horizontal", "vertical", "dropdown"] = Field(
        default="horizontal",
    )
    soft_delete: bool = Field(default=True)
    timestamp_fields: bool = Field(default=True)

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class TableDefaults(DomainModel):
    """Default configuration for DataTables."""

    reorderable_columns: bool = Field(default=False)
    enable_column_visibility: bool = Field(default=True)
    sticky_header: bool = Field(default=True)
    virtualized: bool = Field(default=False)
    row_height: int = Field(default=48, ge=24, le=120)
    zebra_stripes: bool = Field(default=True)
    hover_highlight: bool = Field(default=True)

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class FormDefaults(DomainModel):
    """Default configuration for Forms."""

    show_required_indicator: bool = Field(default=True)
    autosave_enabled: bool = Field(default=False)
    autosave_interval_ms: int = Field(default=30000, ge=1000)
    confirm_unsaved_changes: bool = Field(default=True)
    inline_validation: bool = Field(default=True)

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class ResourceYAMLConfig(DomainModel):
    """Per-resource configuration from YAML."""

    enabled: bool = Field(default=True)
    icon: str | None = None
    label: str | None = None
    label_plural: str | None = None
    per_page: int | None = Field(default=None, ge=1, le=1000)
    searchable_fields: list[str] | None = None
    default_sort: str | None = None
    default_sort_order: Literal["asc", "desc"] = "desc"
    permissions: dict[str, list[str]] | None = None

    model_config = {"extra": "allow"}


@dataclass(init=False)
class AdminNavigationGroup(DomainModel):
    """Navigation group configuration."""

    label: str
    icon: str | None = None
    order: int = Field(default=100, ge=0)
    resources: list[str] = Field(default_factory=list)
    permission: str | None = None
    collapsible: bool = Field(default=True)
    collapsed_by_default: bool = Field(default=False)

    model_config = {"extra": "forbid"}
