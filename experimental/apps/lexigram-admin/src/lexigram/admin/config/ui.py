"""UI, dashboard layout, cluster, and data configurations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False)
class AdminUIConfig(DomainModel):
    """UI/Theme configuration."""

    theme: Literal["light", "dark", "system"] = Field(default="system")
    primary_color: str = Field(default="#6B7280")
    sidebar_width: int = Field(default=256, ge=200, le=400)
    sidebar_collapsed_width: int = Field(default=64, ge=48, le=100)
    content_max_width: int | None = Field(default=None, ge=800)
    logo_url: str | None = None
    favicon_url: str | None = None

    model_config = {"extra": "allow"}


@dataclass(init=False)
class DashboardLayoutConfig(DomainModel):
    """Dashboard layout configuration."""

    widget_refresh_default: int = Field(default=30)
    max_widgets: int = Field(default=20)
    layout: Literal["grid", "masonry"] = Field(default="grid")


@dataclass(init=False)
class ClusterSpec(DomainModel):
    """Declarative description of an extra cluster.

    Registered clusters get a routable center at ``/admin/{slug}`` with
    its own landing page, namespaced child URLs, secondary sidebar, and
    primary-sidebar collapse — no per-cluster code required.
    """

    name: str = Field(description="Cluster key (used to derive slug/group when unset)")
    label: str = Field(description="Display label")
    icon: str | None = Field(default=None, description="Icon name")
    order: int = Field(default=0, description="Sort order in the registry")
    collapsible: bool = Field(default=True)
    collapsed_by_default: bool = Field(default=False)
    slug: str = Field(default="", description="URL segment (defaults to name)")
    group: str = Field(default="", description="Navigation group (defaults to name)")
    description: str | None = Field(default=None)


@dataclass(init=False)
class AdminClustersConfig(DomainModel):
    """Aggregate configuration for cluster centers."""

    extra: list[ClusterSpec] = Field(
        default_factory=list,
        description="Extra clusters beyond the built-in infrastructure cluster",
    )


@dataclass(init=False)
class AdminDataConfig(DomainModel):
    query_timeout_seconds: int = Field(default=5, ge=1, le=120)
