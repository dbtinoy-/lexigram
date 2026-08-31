"""Per-node file attribution (nodes plan N5.3).

Maps generated or previewed file paths to the canvas nodes that own them,
mirroring the frontend's ``nodeForPath`` heuristics (the writer's on-disk
layout). The completed-run tally is persisted in project meta
(``files_by_node``) and returned alongside ``code-preview`` so the UI can
show real per-node file counts instead of schedule estimates.

Edges carry no kind on the backend, so wiring relationships are resolved by
endpoint *config types* (e.g. an edge from a ``RouteConfig`` node to an
``EntityConfig`` node means "this route serves that entity") — the same set
of relationships the frontend encodes as edge kinds.
"""

from __future__ import annotations

from collections.abc import Iterable
import re

from lexigram.builder.graph.models import (
    ApiKeyGroupConfig,
    AuditLogConfig,
    ContractConfig,
    EmailTemplateConfig,
    EntityConfig,
    FileUploadConfig,
    GraphDocument,
    GraphNode,
    MiddlewareConfig,
    RouteConfig,
    SearchIndexConfig,
    ServiceConfig,
    ValidatorConfig,
)

_CONTROLLER = re.compile(r"^src/app/controllers/([a-z0-9_]+)_controller\.py$")
_UPLOAD_STORAGE = re.compile(r"^src/app/uploads/([a-z0-9_]+)_upload_storage\.py$")
_VALIDATOR = re.compile(r"^src/app/validators/([a-z0-9_]+)\.py$")
_SEARCH_REPO = re.compile(
    r"^src/app/repositories/([a-z0-9_]+)_search_repository\.py$"
)
_SEARCH_MIGRATION = re.compile(
    r"^migrations/versions/b\d+_([a-z0-9_]+)_search_fts\.py$"
)
_AUDIT_REPO = re.compile(
    r"^src/app/repositories/([a-z0-9_]+)_audit_repository\.py$"
)
_AUDIT_MIGRATION = re.compile(
    r"^migrations/versions/b\d+_([a-z0-9_]+)_audit_log\.py$"
)
_API_KEY_REPO = re.compile(r"^src/app/repositories/api_key_repository\.py$")
_API_KEY_MIGRATION = re.compile(
    r"^migrations/versions/b\d+_api_keys\.py$"
)
_API_KEYS_AUTH = re.compile(r"^src/app/auth/(?:__init__|api_keys)\.py$")
_EMAIL_SHARED = re.compile(r"^src/app/emails/(?:__init__|mailer)\.py$")
_EMAIL_TEMPLATE = re.compile(r"^src/app/emails/([a-z0-9_]+)\.py$")
_MODEL = re.compile(r"^src/app/models/([a-z0-9_]+)\.py$")
_REPOSITORY = re.compile(r"^src/app/repositories/([a-z0-9_]+)_repository\.py$")
_SERVICE = re.compile(r"^src/app/services/([a-z0-9_]+)_service\.py$")

# Module dirs keyed by their node's *config* name.
_CONFIG_NAME_DIRS: tuple[tuple[str, type], ...] = (
    ("src/app/contracts", ContractConfig),
    ("src/app/middleware", MiddlewareConfig),
)


def files_by_node(
    document: GraphDocument, paths: Iterable[str]
) -> dict[str, list[str]]:
    """Attribute each path to its owning node; unattributed paths are dropped.

    Returns ``{node_id: [paths...]}`` with sorted, de-duplicated path lists
    and sorted keys so callers can persist/compare the tally deterministically.
    """
    by_id: dict[str, GraphNode] = {n.id: n for n in document.nodes}
    entity_nodes = [
        n for n in document.nodes if isinstance(n.config, EntityConfig)
    ]

    def entity_by_name(name: str) -> GraphNode | None:
        return next(
            (
                n
                for n in entity_nodes
                if isinstance(n.config, EntityConfig) and n.config.name == name
            ),
            None,
        )

    def route_for_entity(entity: GraphNode) -> GraphNode | None:
        for edge in document.edges:
            src = by_id.get(edge.src)
            if src is not None and edge.dst == entity.id and isinstance(
                src.config, RouteConfig
            ):
                return src
        return None

    def wired_from_entity(
        entity: GraphNode, config_type: type
    ) -> GraphNode | None:
        for edge in document.edges:
            if edge.src != entity.id:
                continue
            dst = by_id.get(edge.dst)
            if dst is not None and isinstance(dst.config, config_type):
                return dst
        return None

    def node_named(config_type: type, name: str) -> GraphNode | None:
        # ``config_type`` is a runtime variable, so isinstance can't narrow
        # the config union for mypy — go through Any.
        for n in document.nodes:
            # Exact-type match on purpose: config classes are final. getattr
            # (not attribute access) because config_type is a runtime value
            # and mypy cannot narrow the config union through it.
            if type(n.config) is not config_type:
                continue
            if getattr(n.config, "name", None) == name:
                return n
        return None

    tally: dict[str, list[str]] = {}

    def attribute(node: GraphNode | None, path: str) -> None:
        if node is None:
            return
        bucket = tally.setdefault(node.id, [])
        if path not in bucket:
            bucket.append(path)

    for raw in paths:
        norm = raw.replace("\\", "/")

        if (m := _CONTROLLER.match(norm)) is not None:
            stem = m.group(1)
            if stem.endswith("_search"):
                entity = entity_by_name(stem[: -len("_search")])
                attribute(
                    (
                        wired_from_entity(entity, SearchIndexConfig)
                        if entity
                        else None
                    )
                    or entity,
                    norm,
                )
            else:
                entity = entity_by_name(stem)
                attribute(
                    (route_for_entity(entity) if entity else None) or entity,
                    norm,
                )
            continue

        if (m := _UPLOAD_STORAGE.match(norm)) is not None:
            attribute(node_named(FileUploadConfig, m.group(1)), norm)
            continue

        if (m := _VALIDATOR.match(norm)) is not None:
            entity = entity_by_name(m.group(1))
            attribute(
                (wired_from_entity(entity, ValidatorConfig) if entity else None)
                or entity,
                norm,
            )
            continue

        if (m := _SEARCH_REPO.match(norm)) is not None:
            entity = entity_by_name(m.group(1))
            if entity is not None:
                attribute(wired_from_entity(entity, SearchIndexConfig), norm)
            continue

        if (m := _SEARCH_MIGRATION.match(norm)) is not None:
            entity = entity_by_name(m.group(1))
            if entity is not None:
                attribute(wired_from_entity(entity, SearchIndexConfig), norm)
            continue

        if (m := _AUDIT_REPO.match(norm)) is not None:
            entity = entity_by_name(m.group(1))
            if entity is not None:
                attribute(wired_from_entity(entity, AuditLogConfig), norm)
            continue

        if (m := _AUDIT_MIGRATION.match(norm)) is not None:
            entity = entity_by_name(m.group(1))
            if entity is not None:
                attribute(wired_from_entity(entity, AuditLogConfig), norm)
            continue

        # API-key surface files are app-global: attribute them to the first
        # enabled api_key_group node (screen-managed kind, no edges).
        if (
            _API_KEY_REPO.match(norm)
            or _API_KEY_MIGRATION.match(norm)
            or _API_KEYS_AUTH.match(norm)
        ):
            groups = [
                n
                for n in document.nodes
                if isinstance(n.config, ApiKeyGroupConfig)
                and n.config.enabled
            ]
            groups.sort(key=lambda n: getattr(n.config, "name", ""))
            attribute(groups[0] if groups else None, norm)
            continue

        # Email files: the shared init/mailer modules go to the first
        # enabled template; per-template modules to their own node (the
        # shared check must win — the template regex also matches their
        # names).
        if _EMAIL_SHARED.match(norm):
            templates = [
                n
                for n in document.nodes
                if isinstance(n.config, EmailTemplateConfig)
                and n.config.enabled
            ]
            templates.sort(key=lambda n: getattr(n.config, "name", ""))
            attribute(templates[0] if templates else None, norm)
            continue
        if (m := _EMAIL_TEMPLATE.match(norm)) is not None:
            templates = [
                n
                for n in document.nodes
                if isinstance(n.config, EmailTemplateConfig)
                and n.config.enabled
                and n.config.name == m.group(1)
            ]
            attribute(templates[0] if templates else None, norm)
            continue

        if (m := _MODEL.match(norm)) is not None:
            attribute(entity_by_name(m.group(1)), norm)
            continue

        if (m := _REPOSITORY.match(norm)) is not None:
            attribute(entity_by_name(m.group(1)), norm)
            continue

        if (m := _SERVICE.match(norm)) is not None:
            entity = entity_by_name(m.group(1))
            attribute(
                (wired_from_entity(entity, ServiceConfig) if entity else None)
                or entity,
                norm,
            )
            continue

        matched_config = False
        for directory, config_type in _CONFIG_NAME_DIRS:
            prefix = directory + "/"
            if norm.startswith(prefix) and norm.endswith(".py"):
                stem = norm[len(prefix) : -len(".py")]
                if "/" not in stem:
                    attribute(node_named(config_type, stem), norm)
                    matched_config = True
                    break
        if matched_config:
            continue

    return {node: sorted(set(paths)) for node, paths in sorted(tally.items())}
