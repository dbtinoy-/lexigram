"""Derive composition module cards from a graph document."""

from __future__ import annotations

from dataclasses import dataclass, replace

from lexigram.builder.graph.models import GraphDocument, GraphNode, ModuleConfig


@dataclass(frozen=True, slots=True)
class ModuleCard:
    id: str
    lexigram: str
    on: bool
    count: int
    kinds: tuple[str, ...]
    reserved: str | None = None


def module_import_graph(document: GraphDocument) -> dict[str, set[str]]:
    """Return ``{slug: slugs it imports}``, derived from frame-to-frame edges.

    Imports are never stored on ``ModuleConfig`` (taxonomy rule M2): the
    edges already say it, and a second copy is a second thing to keep
    correct. Both the validator (cycle detection) and the module emitter
    (the ``imports`` list in the boundary) read this one function, so a
    graph can never validate as acyclic and then emit a cycle.

    Self-imports are dropped rather than reported here -- diagnosing them is
    the validator's job, and the emitter must not render one either way.
    """
    slug_by_id = {
        node.id: node.config.name
        for node in document.nodes
        if node.kind == "module" and isinstance(node.config, ModuleConfig)
    }
    imports: dict[str, set[str]] = {slug: set() for slug in slug_by_id.values()}
    for edge in document.edges:
        importer = slug_by_id.get(edge.src)
        imported = slug_by_id.get(edge.dst)
        if importer is None or imported is None or importer == imported:
            continue
        imports[importer].add(imported)
    return imports


def is_muted(node: GraphNode) -> bool:
    """True when *node* is on the canvas but excluded from generation.

    Public because muting is a contract, not an implementation detail: the
    canvas, the module map and the writer must all agree on which nodes are
    live, and a private predicate invites each of them to re-derive it.
    """
    if getattr(node, "muted", False):
        return True
    # Canvas-shaped input (a raw dict still carrying its ``meta`` bag) can
    # reach here from fixtures and from clients that have not been parsed
    # yet; the parsed document is the normal path.
    meta = getattr(node, "meta", None)
    if isinstance(meta, dict):
        return bool(meta.get("muted"))
    return bool(getattr(meta, "muted", False)) if meta is not None else False


def drop_muted(doc: GraphDocument) -> GraphDocument:
    """*doc* with muted nodes -- and every edge touching one -- removed.

    Returns a new document; muting must never mutate the graph the user is
    editing. Edges go too, because an edge to a node that will not be
    generated is a dangling reference the emitters would have to guess
    about.

    Only edges touching a *muted* node are removed -- an edge pointing at an
    id that never existed is a broken graph, and dropping it here would
    quietly delete the evidence before the validator can report it.
    """
    live = [node for node in doc.nodes if not is_muted(node)]
    muted_ids = {node.id for node in doc.nodes if is_muted(node)}
    edges = [
        edge
        for edge in doc.edges
        if edge.src not in muted_ids and edge.dst not in muted_ids
    ]
    return replace(doc, nodes=live, edges=edges)


def derive_modules(doc: GraphDocument) -> list[ModuleCard]:
    """Return module-map cards (mirrors playground ``modulesFromGraph``)."""
    live = [node for node in doc.nodes if not is_muted(node)]
    counts: dict[str, int] = {}
    for node in live:
        counts[node.kind] = counts.get(node.kind, 0) + 1

    def n(*kinds: str) -> int:
        return sum(counts.get(k, 0) for k in kinds)

    def card(
        id_: str,
        lexigram: str,
        on: bool,
        count: int,
        kinds: tuple[str, ...],
        reserved: str | None = None,
    ) -> ModuleCard:
        return ModuleCard(id_, lexigram, on, count, kinds, reserved)

    search_note: str | None = None
    if n("search_index") > 0:
        search_note = "meilisearch reserved"
        for node in live:
            cfg = node.config
            engine = getattr(cfg, "engine", None) if cfg is not None else None
            if engine in {"meilisearch", "elasticsearch"}:
                search_note = "meilisearch/elasticsearch reserved — FTS/LIKE emit"
                break

    cache_note: str | None = None
    for node in live:
        cfg = node.config
        if node.kind == "cache" and getattr(cfg, "backend", None) == "redis":
            cache_note = "Redis reserved — CacheModule uses in-process memory"
            break

    gql = n("graphql")
    return [
        card("web", "WebModule", True, n("route", "middleware", "interceptor", "exception_filter", "file_upload"), ("route", "middleware", "interceptor", "exception_filter", "file_upload")),
        card("sql", "DatabaseModule", n("entity") > 0, n("entity", "seeder", "search_index", "audit_log"), ("entity", "seeder", "search_index", "audit_log"), search_note),
        card("auth", "AuthModule", n("auth", "role", "api_key_group") > 0, n("auth", "role", "api_key_group"), ("auth", "role", "api_key_group", "auth_policy")),
        card("features", "FlagManager", n("feature_flag") > 0, n("feature_flag"), ("feature_flag",)),
        card("events", "EventsModule", n("event", "event_handler", "command", "query", "projection", "saga") > 0, n("event", "event_handler", "command", "query", "projection", "saga"), ("event", "event_handler", "command", "query", "projection", "saga")),
        card("tasks", "TasksModule", n("cron", "job") > 0, n("cron", "job"), ("cron", "job"), "queue backend reserved"),
        card("cache", "CacheModule", n("cache") > 0, n("cache"), ("cache",), cache_note),
        card("graphql", "GraphQLModule", gql > 0, gql, ("graphql", "dataloader"), None),
        card("monitor", "MonitorModule", n("health", "metric") > 0, n("health", "metric"), ("health", "metric")),
        card("mail", "Mailable", n("email_template") > 0, n("email_template"), ("email_template",)),
        card("realtime", "websocket", n("realtime_channel") > 0, n("realtime_channel"), ("realtime_channel",)),
        card("webhook", "lexigram-webhook", n("webhook") > 0, n("webhook"), ("webhook",)),
        card("http", "BaseURLHTTPClient", n("api_client") > 0, n("api_client"), ("api_client",)),
        card("storage", "AbstractDriver", n("storage_driver") > 0, n("storage_driver"), ("storage_driver",)),
        card("queue", "lexigram-queue", False, 0, (), "not emitting"),
        card("resilience", "lexigram-resilience", False, 0, (), "not emitting"),
        card("secrets", "lexigram-secrets", False, 0, (), "not emitting"),
        card("tenancy", "tenant_resolver", False, 0, (), "not emitting"),
        card("workflow", "lexigram-workflow", False, 0, (), "not emitting"),
        card("nosql", "document_repo", False, 0, (), "SQL is v1 persistence"),
    ]


__all__ = ["ModuleCard", "derive_modules"]
