"""Graph document domain models (frozen, source-of-truth canvas state)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Position:
    """Canvas coordinates."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class AppSettingsConfig:
    """Single per-graph application settings node."""

    app_name: str
    port: int
    db: str


@dataclass(frozen=True, slots=True)
class FieldConfig:
    """One entity field."""

    name: str
    type: str
    nullable: bool = False


@dataclass(frozen=True, slots=True)
class EntityConfig:
    """An entity node: snake_case name plus one or more fields."""

    name: str
    fields: tuple[FieldConfig, ...]


@dataclass(frozen=True, slots=True)
class RouteConfig:
    """A route node bound to an entity via an edge."""

    ops: tuple[str, ...]
    path_prefix: str | None = None


@dataclass(frozen=True, slots=True)
class GraphNode:
    """A canvas node."""

    id: str
    kind: str
    position: Position
    config: NodeConfig | None


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """A typed canvas edge."""

    id: str
    src: str
    dst: str


@dataclass(frozen=True, slots=True)
class GraphDocument:
    """The source-of-truth canvas document."""

    version: int
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


@dataclass(frozen=True, slots=True)
class ValidatedGraph:
    """A graph that passed validation, with kind-filtered accessors."""

    document: GraphDocument

    def settings(self) -> GraphNode:
        """Return the single app_settings node."""
        return next(n for n in self.document.nodes if n.kind == "app_settings")

    def entities(self) -> list[GraphNode]:
        """Return all entity nodes in document order."""
        return [n for n in self.document.nodes if n.kind == "entity"]

    def routes(self) -> list[GraphNode]:
        """Return all route nodes in document order."""
        return [n for n in self.document.nodes if n.kind == "route"]


NodeConfig = AppSettingsConfig | EntityConfig | RouteConfig
