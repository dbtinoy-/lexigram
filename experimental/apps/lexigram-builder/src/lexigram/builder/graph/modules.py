"""Derive composition module cards from a graph document."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.builder.graph.models import GraphDocument, GraphNode


@dataclass(frozen=True, slots=True)
class ModuleCard:
    id: str
    lexigram: str
    on: bool
    count: int
    kinds: tuple[str, ...]
    reserved: str | None = None


def _muted(node: GraphNode) -> bool:
    meta = getattr(node, "meta", None)
    if isinstance(meta, dict):
        return bool(meta.get("muted"))
    return bool(getattr(meta, "muted", False)) if meta is not None else False


def derive_modules(doc: GraphDocument) -> list[ModuleCard]:
    """Return module-map cards (mirrors playground ``modulesFromGraph``)."""
    live = [node for node in doc.nodes if not _muted(node)]
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
        card("web", "WebModule", True, n("route", "middleware", "exception_filter", "file_upload"), ("route", "middleware", "exception_filter", "file_upload")),
        card("sql", "DatabaseModule", n("entity") > 0, n("entity", "seeder", "search_index", "audit_log"), ("entity", "seeder", "search_index", "audit_log"), search_note),
        card("auth", "AuthModule", n("auth", "role", "api_key_group") > 0, n("auth", "role", "api_key_group"), ("auth", "role", "api_key_group")),
        card("features", "FlagManager", n("feature_flag") > 0, n("feature_flag"), ("feature_flag",)),
        card("events", "EventsModule", n("event", "event_handler", "command", "query", "projection") > 0, n("event", "event_handler", "command", "query", "projection"), ("event", "event_handler", "command", "query", "projection"), "saga reserved"),
        card("tasks", "TasksModule", n("cron", "job") > 0, n("cron", "job"), ("cron", "job"), "queue backend reserved"),
        card("cache", "CacheModule", n("cache") > 0, n("cache"), ("cache",), cache_note),
        card("graphql", "GraphQLModule", gql > 0, gql, ("graphql",), "dataloader reserved" if gql else None),
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
