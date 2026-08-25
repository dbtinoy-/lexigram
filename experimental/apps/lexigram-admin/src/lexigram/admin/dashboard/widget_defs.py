"""Admin dashboard widget type definitions.

Provides WidgetType, WidgetConfig, DashboardConfig and the widget/store
protocols plus the in-memory persistence implementation used for legacy
dashboard builder assembly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol


class WidgetType(StrEnum):
    """Widget types for legacy dashboard builder."""

    METRIC = "metric"
    CHART = "chart"
    TABLE = "table"
    TEXT = "text"
    CUSTOM = "custom"
    STAT_CARD = "stat_card"
    ACTIVITY = "activity"
    HEALTH = "health"


@dataclass
class WidgetConfig:
    """Widget configuration."""

    id: str
    type: WidgetType
    title: str
    config: dict[str, Any] = field(default_factory=dict)
    position: dict[str, int] = field(
        default_factory=lambda: {"x": 0, "y": 0, "w": 1, "h": 1},
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "config": self.config,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WidgetConfig:
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            type=WidgetType(data["type"]),
            title=data["title"],
            config=data.get("config", {}),
            position=data.get("position", {"x": 0, "y": 0, "w": 1, "h": 1}),
        )


@dataclass
class DashboardConfig:
    """Dashboard configuration."""

    id: str
    name: str
    widgets: list[WidgetConfig] = field(default_factory=list)
    layout: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "widgets": [w.to_dict() for w in self.widgets],
            "layout": self.layout,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DashboardConfig:
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            widgets=[WidgetConfig.from_dict(w) for w in data.get("widgets", [])],
            layout=data.get("layout", {}),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat()),
            ),
            updated_at=datetime.fromisoformat(
                data.get("updated_at", datetime.now().isoformat()),
            ),
        )


class IWidget(Protocol):
    """Protocol for dashboard widgets."""

    async def render(self, config: dict[str, Any]) -> str:
        """Render widget HTML (async)."""
        ...

    def get_default_config(self) -> dict[str, Any]:
        """Get default widget configuration."""
        ...


class IDashboardStore(Protocol):
    """Protocol for dashboard persistence (async)."""

    async def save(self, dashboard: DashboardConfig) -> bool:
        """Save dashboard configuration."""
        ...

    async def load(self, dashboard_id: str) -> DashboardConfig | None:
        """Load dashboard configuration."""
        ...

    async def list(self) -> list[DashboardConfig]:
        """List all dashboards."""
        ...

    async def delete(self, dashboard_id: str) -> bool:
        """Delete dashboard."""
        ...


class InMemoryDashboardStore:
    """In-memory dashboard storage implementation."""

    def __init__(self) -> None:
        """Initialize store."""
        self.dashboards: dict[str, DashboardConfig] = {}

    async def save(self, dashboard: DashboardConfig) -> bool:
        """Save dashboard."""
        dashboard.updated_at = datetime.now()
        self.dashboards[dashboard.id] = dashboard
        return True

    async def load(self, dashboard_id: str) -> DashboardConfig | None:
        """Load dashboard."""
        return self.dashboards.get(dashboard_id)

    async def list(self) -> list[DashboardConfig]:
        """List all dashboards."""
        return list(self.dashboards.values())

    async def delete(self, dashboard_id: str) -> bool:
        """Delete dashboard."""
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]
            return True
        return False


__all__ = [
    "DashboardConfig",
    "IDashboardStore",
    "IWidget",
    "InMemoryDashboardStore",
    "WidgetConfig",
    "WidgetType",
]
