"""Fill node configs from the edges the canvas actually drew.

Three node kinds carry a binding the inspector may leave blank because the
canvas is the real source of truth: a command/query is bound to an aggregate,
a projection consumes events, a handler listens to one event. Each resolver
reads that binding off the wired edge and falls back to the node's own field,
so a graph authored by drawing and a graph authored by typing generate the
same project.

These are pure functions over a ``GraphDocument`` -- no filesystem, no
layout, no writer state -- which is why they live outside ``writer.py``.
"""

from __future__ import annotations

from lexigram.builder.graph.models import (
    CqrsMessageConfig,
    EntityConfig,
    EventConfig,
    EventHandlerConfig,
    GraphDocument,
    GraphNode,
    ProjectionConfig,
)

__all__ = ["resolve_cqrs", "resolve_handlers", "resolve_projections"]


def resolve_cqrs(
    messages: list[CqrsMessageConfig],
    document: GraphDocument,
    by_id: dict[str, GraphNode],
) -> list[CqrsMessageConfig]:
    """Fill each command/query's bound ``entity`` from its wired edge.

    An ``entity -> command|query`` edge binds the handler's aggregate
    (repository injected at registration). The node's own ``entity`` field
    is a fallback.
    """
    entity_for_msg: dict[str, str] = {}
    for edge in document.edges:
        src = by_id.get(edge.src)
        dst = by_id.get(edge.dst)
        if (
            src is not None
            and dst is not None
            and src.kind == "entity"
            and dst.kind in ("command", "query")
            and isinstance(src.config, EntityConfig)
            and isinstance(dst.config, CqrsMessageConfig)
        ):
            entity_for_msg[dst.id] = src.config.name
    resolved: list[CqrsMessageConfig] = []
    for node in document.nodes:
        if node.kind not in ("command", "query") or not isinstance(
            node.config, CqrsMessageConfig
        ):
            continue
        if node.config not in messages:
            continue
        entity_name = entity_for_msg.get(node.id) or node.config.entity
        resolved.append(
            CqrsMessageConfig(
                name=node.config.name,
                side=node.config.side,
                entity=entity_name,
                fields=node.config.fields,
                enabled=True,
                description=node.config.description,
            )
        )
    return sorted(resolved, key=lambda m: (m.side, m.name))


def resolve_projections(
    projections: list[ProjectionConfig],
    document: GraphDocument,
    by_id: dict[str, GraphNode],
) -> list[ProjectionConfig]:
    """Fill each projection's consumed events from its wired edges.

    An ``event -> projection`` edge feeds that event into the projection's
    read model; the projection's own ``events`` field is a fallback.
    """
    events_for_projection: dict[str, list[str]] = {}
    for edge in document.edges:
        src = by_id.get(edge.src)
        dst = by_id.get(edge.dst)
        if (
            src is not None
            and dst is not None
            and src.kind == "event"
            and dst.kind == "projection"
            and isinstance(src.config, EventConfig)
            and isinstance(dst.config, ProjectionConfig)
        ):
            events_for_projection.setdefault(dst.id, []).append(src.config.name)
    resolved: list[ProjectionConfig] = []
    for node in document.nodes:
        if node.kind != "projection" or not isinstance(node.config, ProjectionConfig):
            continue
        if node.config not in projections:
            continue
        wired = events_for_projection.get(node.id, [])
        merged = list(dict.fromkeys([*wired, *node.config.events]))
        if not merged:
            # No events to consume — nothing useful to wire; skip.
            continue
        resolved.append(
            ProjectionConfig(
                name=node.config.name,
                events=tuple(merged),
                enabled=True,
                description=node.config.description,
            )
        )
    return sorted(resolved, key=lambda p: p.name)


def resolve_handlers(
    handlers: list[EventHandlerConfig],
    document: GraphDocument,
    by_id: dict[str, GraphNode],
) -> list[EventHandlerConfig]:
    """Fill each handler's ``event`` from its wired ``event -> handler`` edge.

    The handler's own config may name an event explicitly; an edge to an event
    node takes precedence (the canvas is the source of truth for wiring).
    """
    # Map handler node id -> the event name it is wired to.
    event_for_handler: dict[str, str] = {}
    for edge in document.edges:
        src = by_id.get(edge.src)
        dst = by_id.get(edge.dst)
        if (
            src is not None
            and dst is not None
            and src.kind == "event"
            and dst.kind == "event_handler"
            and isinstance(src.config, EventConfig)
            and isinstance(dst.config, EventHandlerConfig)
        ):
            event_for_handler[dst.id] = src.config.name
    resolved: list[EventHandlerConfig] = []
    for node in document.nodes:
        if node.kind != "event_handler" or not isinstance(
            node.config, EventHandlerConfig
        ):
            continue
        if node.config not in handlers:
            continue
        wired = event_for_handler.get(node.id)
        event_name = wired or node.config.event
        if event_name:
            resolved.append(
                EventHandlerConfig(
                    name=node.config.name,
                    event=event_name,
                    enabled=True,
                    description=node.config.description,
                )
            )
    return resolved
