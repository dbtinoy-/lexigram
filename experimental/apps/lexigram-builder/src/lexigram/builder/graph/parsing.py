"""JSON <-> GraphDocument conversion for the projects store."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from lexigram.builder.exceptions import GraphValidationError
from lexigram.builder.graph.models import (
    AppSettingsConfig,
    EntityConfig,
    FieldConfig,
    GraphDocument,
    GraphEdge,
    GraphNode,
    Position,
    RouteConfig,
)
from lexigram.builder.graph.palette import KNOWN_KINDS
from lexigram.result import Err, Ok, Result


def document_to_dict(document: GraphDocument) -> dict[str, Any]:
    """Serialize a graph document to its JSON-ready dict form."""
    nodes: list[dict[str, Any]] = []
    for node in document.nodes:
        entry: dict[str, Any] = {
            "id": node.id,
            "kind": node.kind,
            "position": asdict(node.position),
        }
        if isinstance(node.config, AppSettingsConfig):
            entry["config"] = asdict(node.config)
        elif isinstance(node.config, EntityConfig):
            cfg = asdict(node.config)
            cfg["fields"] = [asdict(f) for f in node.config.fields]
            entry["config"] = cfg
        elif isinstance(node.config, RouteConfig):
            entry["config"] = {
                "ops": list(node.config.ops),
                "path_prefix": node.config.path_prefix,
            }
        else:
            entry["config"] = None
        nodes.append(entry)
    return {
        "version": document.version,
        "nodes": nodes,
        "edges": [asdict(e) for e in document.edges],
    }


def parse_document(data: dict[str, Any]) -> Result[GraphDocument, GraphValidationError]:
    """Parse and type a graph document dict; structural errors are Err."""
    try:
        version = int(data["version"])
        raw_nodes = data.get("nodes", [])
        raw_edges = data.get("edges", [])
        nodes: list[GraphNode] = []
        for raw in raw_nodes:
            pos = Position(x=float(raw["position"]["x"]), y=float(raw["position"]["y"]))
            kind = str(raw["kind"])
            if kind not in KNOWN_KINDS:
                return Err(GraphValidationError(f"unknown node kind {kind!r}"))
            config: AppSettingsConfig | EntityConfig | RouteConfig | None = None
            raw_cfg = raw.get("config")
            if kind == "app_settings":
                config = AppSettingsConfig(
                    app_name=str(raw_cfg["app_name"]),
                    port=int(raw_cfg["port"]),
                    db=str(raw_cfg["db"]),
                )
            elif kind == "entity":
                fields = tuple(
                    FieldConfig(
                        name=str(f["name"]),
                        type=str(f["type"]),
                        nullable=bool(f.get("nullable", False)),
                    )
                    for f in raw_cfg.get("fields", [])
                )
                config = EntityConfig(name=str(raw_cfg["name"]), fields=fields)
            elif kind == "route":
                ops_raw = raw_cfg.get("ops", [])
                prefix = raw_cfg.get("path_prefix")
                config = RouteConfig(
                    ops=tuple(str(o) for o in ops_raw),
                    path_prefix=None if prefix is None else str(prefix),
                )
            nodes.append(
                GraphNode(id=str(raw["id"]), kind=kind, position=pos, config=config)
            )
        edges = [
            GraphEdge(id=str(e["id"]), src=str(e["src"]), dst=str(e["dst"]))
            for e in raw_edges
        ]
        return Ok(
            GraphDocument(version=version, nodes=tuple(nodes), edges=tuple(edges))
        )
    except (KeyError, TypeError, ValueError) as exc:
        return Err(GraphValidationError(f"malformed graph document: {exc}"))
