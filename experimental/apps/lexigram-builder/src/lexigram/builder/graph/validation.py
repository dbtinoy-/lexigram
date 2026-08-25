"""Graph validation producing node-scoped diagnostics."""

from __future__ import annotations

from lexigram.builder.exceptions import GraphValidationError
from lexigram.builder.graph.models import (
    AppSettingsConfig,
    EntityConfig,
    GraphDocument,
    GraphNode,
    RouteConfig,
    ValidatedGraph,
)
from lexigram.builder.graph.palette import (
    ALLOWED_EDGES,
    DB_PRESETS,
    ENTITY_OPS,
    FIELD_TYPES,
    is_known_kind,
    is_snake_case_identifier,
    is_valid_port,
)
from lexigram.builder.types import Diagnostic, DiagnosticSeverity
from lexigram.result import Err, Ok, Result


def validate(document: GraphDocument) -> Result[ValidatedGraph, GraphValidationError]:
    """Validate *document* and return a :class:`ValidatedGraph` or aggregated errors.

    All rules run; diagnostics are aggregated (no fail-fast) so the canvas
    can badge every offending node in one pass.
    """
    diagnostics: list[Diagnostic] = []

    by_id: dict[str, GraphNode] = {}
    for node in document.nodes:
        if node.id in by_id:
            diagnostics.append(
                Diagnostic(
                    node_id=node.id,
                    severity=DiagnosticSeverity.ERROR,
                    code="duplicate-node-id",
                    message=f"Node id {node.id!r} appears more than once",
                )
            )
        else:
            by_id[node.id] = node

    settings_nodes = [n for n in document.nodes if n.kind == "app_settings"]
    if len(settings_nodes) == 0:
        diagnostics.append(
            Diagnostic(
                node_id=None,
                severity=DiagnosticSeverity.ERROR,
                code="missing-app-settings",
                message="Graph requires exactly one app_settings node",
            )
        )
    elif len(settings_nodes) > 1:
        for extra in settings_nodes[1:]:
            diagnostics.append(
                Diagnostic(
                    node_id=extra.id,
                    severity=DiagnosticSeverity.ERROR,
                    code="duplicate-app-settings",
                    message="Only one app_settings node is allowed per graph",
                )
            )

    entity_names: dict[str, str] = {}
    for node in document.nodes:
        diagnostics.extend(_check_node(node, entity_names))

    node_ids = set(by_id)
    for edge in document.edges:
        src_kind = by_id[edge.src].kind if edge.src in by_id else None
        dst_kind = by_id[edge.dst].kind if edge.dst in by_id else None
        if edge.src not in node_ids or edge.dst not in node_ids:
            diagnostics.append(
                Diagnostic(
                    node_id=edge.src if edge.src not in node_ids else edge.dst,
                    severity=DiagnosticSeverity.ERROR,
                    code="unknown-edge-endpoint",
                    message=(
                        f"Edge {edge.id!r} references unknown endpoint "
                        f"({edge.src!r}, {edge.dst!r})"
                    ),
                )
            )
        elif (src_kind, dst_kind) not in ALLOWED_EDGES:
            diagnostics.append(
                Diagnostic(
                    node_id=edge.src,
                    severity=DiagnosticSeverity.ERROR,
                    code="bad-edge-types",
                    message=f"Edges must connect route -> entity, got {src_kind} -> {dst_kind}",
                )
            )

    connected_route_ids = {e.src for e in document.edges if e.src in node_ids}
    for node in document.nodes:
        if node.kind == "route" and node.id not in connected_route_ids:
            diagnostics.append(
                Diagnostic(
                    node_id=node.id,
                    severity=DiagnosticSeverity.ERROR,
                    code="orphan-route",
                    message="Route nodes must be wired to an entity",
                )
            )

    errors = [d for d in diagnostics if d.severity is DiagnosticSeverity.ERROR]
    if errors:
        return Err(
            GraphValidationError(
                f"Graph validation failed with {len(errors)} error(s)",
                diagnostics=tuple(diagnostics),
            )
        )
    return Ok(ValidatedGraph(document=document))


def _check_node(node: GraphNode, entity_names: dict[str, str]) -> list[Diagnostic]:
    """Kind-dispatch a single node's config checks."""
    if not is_known_kind(node.kind):
        return [
            Diagnostic(
                node_id=node.id,
                severity=DiagnosticSeverity.ERROR,
                code="unknown-kind",
                message=f"Unknown node kind {node.kind!r}",
            )
        ]
    if isinstance(node.config, AppSettingsConfig):
        return _check_app_settings(node)
    if isinstance(node.config, EntityConfig):
        return _check_entity(node, entity_names)
    if isinstance(node.config, RouteConfig):
        return _check_route(node)
    return []


def _diag(node: GraphNode, code: str, message: str) -> Diagnostic:
    return Diagnostic(
        node_id=node.id, severity=DiagnosticSeverity.ERROR, code=code, message=message
    )


def _check_app_settings(node: GraphNode) -> list[Diagnostic]:
    config: AppSettingsConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.app_name):
        out.append(_diag(node, "invalid-app-name", "app_name must be snake_case"))
    if not is_valid_port(config.port):
        out.append(
            _diag(node, "port-out-of-range", f"port {config.port} outside 1024-65535")
        )
    if config.db not in DB_PRESETS:
        out.append(
            _diag(
                node,
                "invalid-db-preset",
                f"db must be one of {sorted(DB_PRESETS)}",
            )
        )
    return out


def _check_entity(node: GraphNode, entity_names: dict[str, str]) -> list[Diagnostic]:
    config: EntityConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(_diag(node, "invalid-entity-name", "name must be snake_case"))
    elif config.name in entity_names:
        out.append(
            _diag(
                node,
                "duplicate-entity-name",
                f"Entity name {config.name!r} already used by {entity_names[config.name]}",
            )
        )
    else:
        entity_names[config.name] = node.id

    if not config.fields:
        out.append(_diag(node, "no-fields", "Entities require at least one field"))

    seen_fields: set[str] = set()
    for field in config.fields:
        if field.name in seen_fields:
            out.append(
                _diag(node, "duplicate-field", f"Field {field.name!r} duplicated")
            )
        seen_fields.add(field.name)
        if not is_snake_case_identifier(field.name):
            out.append(_diag(node, "invalid-field-name", f"Field name {field.name!r}"))
        if field.type not in FIELD_TYPES:
            out.append(
                _diag(
                    node,
                    "unknown-field-type",
                    f"type {field.type!r} not in {sorted(FIELD_TYPES)}",
                )
            )
    return out


def _check_route(node: GraphNode) -> list[Diagnostic]:
    config: RouteConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not config.ops:
        out.append(_diag(node, "no-ops", "Routes require at least one op"))
    unknown_ops = sorted(set(config.ops) - ENTITY_OPS)
    if unknown_ops:
        out.append(
            _diag(node, "unknown-op", f"ops {unknown_ops} not in {sorted(ENTITY_OPS)}")
        )
    prefix = config.path_prefix
    if prefix is not None and (not prefix or any(c.isspace() for c in prefix)):
        out.append(_diag(node, "invalid-path-prefix", "path_prefix must be non-blank"))
    return out


__all__ = ["validate"]
