"""JSON <-> GraphDocument conversion for the projects store."""

from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any

from lexigram.result import Err, Ok, Result

from lexigram.builder.exceptions import GraphValidationError
from lexigram.builder.graph.models import (
    APP_FEATURE_KEYS,
    ApiKeyGroupConfig,
    ApiKeyPermission,
    AppSettingsConfig,
    AuditLogConfig,
    AuthConfig,
    CacheConfig,
    ChannelConfig,
    ContractConfig,
    CqrsMessageConfig,
    CronConfig,
    EmailTemplateConfig,
    EmailVariable,
    EntityConfig,
    ErrorConfig,
    EventConfig,
    EventHandlerConfig,
    ExceptionFilterConfig,
    FeatureFlagConfig,
    FieldConfig,
    FileUploadConfig,
    GraphDocument,
    GraphEdge,
    GraphNode,
    GraphQLConfig,
    HealthConfig,
    JobConfig,
    MetricConfig,
    SagaConfig,
    ApiClientConfig,
    StorageDriverConfig,
    MiddlewareConfig,
    Position,
    ProjectionConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
    SearchIndexConfig,
    SeederConfig,
    ServiceConfig,
    ThumbnailSize,
    ValidatorConfig,
    WebhookConfig,
)
from lexigram.builder.graph.palette import KNOWN_KINDS, normalize_structure

_TTL_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _ttl_seconds(value: Any) -> int:
    """Coerce a TTL value to seconds.

    Accepts an int/float of seconds or a duration string like ``"5m"``,
    ``"300s"``, ``"1h"`` (the frontend TTL field). Falls back to 300s.
    """
    if isinstance(value, bool):
        return 300
    if isinstance(value, (int, float)):
        return max(1, int(value))
    if isinstance(value, str):
        text = value.strip().lower()
        if text.isdigit():
            return max(1, int(text))
        match = re.fullmatch(r"(\d+)\s*([smhd])?", text)
        if match:
            amount = int(match.group(1))
            unit = match.group(2) or "s"
            return max(1, amount * _TTL_UNIT_SECONDS[unit])
    return 300


def _event_payload(raw_cfg: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract an event's payload fields from either a ``payload`` list of
    ``{name, type}`` objects or a ``schema`` ``{name: type}`` object."""
    fields: list[tuple[str, str]] = []
    payload = raw_cfg.get("payload")
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and item.get("name"):
                fields.append((str(item["name"]), str(item.get("type", "str"))))
    schema = raw_cfg.get("schema")
    if not fields and isinstance(schema, dict):
        fields.extend((str(name), str(typ)) for name, typ in schema.items())
    return fields


def _flatten_permissions(raw: Any) -> tuple[str, ...]:
    """Flatten the frontend's per-resource permission objects into
    ``resource.action`` strings for codegen.

    Accepts ``[{"resource": "notes", "actions": ["create", "read"]}]`` and
    tolerates plain string lists (already flattened) and junk entries.
    """
    out: list[str] = []
    if not isinstance(raw, list):
        return ()
    for item in raw:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict) and item.get("resource"):
            resource = str(item["resource"])
            for action in item.get("actions") or []:
                if isinstance(action, str):
                    out.append(f"{resource}.{action}")
    return tuple(dict.fromkeys(out))


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
            cfg = asdict(node.config)
            # Round-trip features as the frontend's {key: bool} object.
            enabled = node.config.features
            cfg["features"] = {key: (key in enabled) for key in APP_FEATURE_KEYS}
            entry["config"] = cfg
        elif isinstance(node.config, EntityConfig):
            cfg = asdict(node.config)
            cfg["fields"] = [asdict(f) for f in node.config.fields]
            entry["config"] = cfg
        elif isinstance(node.config, RouteConfig):
            entry["config"] = {
                "ops": list(node.config.ops),
                "path_prefix": node.config.path_prefix,
            }
        elif isinstance(node.config, MiddlewareConfig):
            entry["config"] = {
                "name": node.config.name,
                "type": node.config.type,
                "order": node.config.order,
            }
        elif isinstance(node.config, CronConfig):
            entry["config"] = {
                "name": node.config.name,
                "schedule": node.config.schedule,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, WebhookConfig):
            entry["config"] = {
                "name": node.config.name,
                "path": node.config.path,
                "verify_signature": node.config.verify_signature,
                "secret_env": node.config.secret_env,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, JobConfig | ServiceConfig | SeederConfig):
            entry["config"] = {
                "name": node.config.name,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, CacheConfig):
            entry["config"] = {
                "name": node.config.name,
                "ttl": node.config.ttl,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, GraphQLConfig):
            entry["config"] = {
                "name": node.config.name,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, HealthConfig):
            entry["config"] = {
                "name": node.config.name,
                "critical": node.config.critical,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, EventConfig):
            entry["config"] = {
                "name": node.config.name,
                "payload": [
                    {"name": name, "type": typ} for name, typ in node.config.payload
                ],
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, EventHandlerConfig):
            entry["config"] = {
                "name": node.config.name,
                "event": node.config.event,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, CqrsMessageConfig):
            entry["config"] = {
                "name": node.config.name,
                "side": node.config.side,
                "entity": node.config.entity,
                "fields": [
                    {"name": name, "type": typ}
                    for name, typ in node.config.fields
                ],
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, ProjectionConfig):
            entry["config"] = {
                "name": node.config.name,
                "events": list(node.config.events),
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, MetricConfig):
            entry["config"] = {
                "name": node.config.name,
                "unit": node.config.unit,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, SagaConfig):
            entry["config"] = {
                "name": node.config.name,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, ApiClientConfig):
            entry["config"] = {
                "name": node.config.name,
                "base_url": node.config.base_url,
                "auth_type": node.config.auth_type,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, StorageDriverConfig):
            entry["config"] = {
                "name": node.config.name,
                "driver_type": node.config.driver_type,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, ExceptionFilterConfig):
            entry["config"] = {
                "name": node.config.name,
                "exception_type": node.config.exception_type,
                "status_code": node.config.status_code,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, ErrorConfig):
            entry["config"] = {
                "name": node.config.name,
                "status_code": node.config.status_code,
                "error_code": node.config.error_code,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, ChannelConfig):
            entry["config"] = {
                "name": node.config.name,
                "path": node.config.path,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, FeatureFlagConfig):
            entry["config"] = {
                "name": node.config.name,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, AuthConfig):
            entry["config"] = {
                "name": node.config.name,
                "provider": node.config.provider,
                "login_path": node.config.login_path,
                "refresh_token": node.config.refresh_token,
                "token_expiry": node.config.token_expiry,
                "description": node.config.description,
            }
        elif isinstance(node.config, RoleConfig):
            entry["config"] = {
                "name": node.config.name,
                "permissions": list(node.config.permissions),
                "inherits": list(node.config.inherits),
                "is_default": node.config.is_default,
                "description": node.config.description,
            }
        elif isinstance(node.config, RateLimitConfig):
            entry["config"] = {
                "name": node.config.name,
                "strategy": node.config.strategy,
                "window_seconds": node.config.window_seconds,
                "max_requests": node.config.max_requests,
                "key_by": node.config.key_by,
                "description": node.config.description,
            }
        elif isinstance(node.config, ContractConfig):
            entry["config"] = {
                "name": node.config.name,
                "direction": node.config.direction,
                "fields": [
                    {"name": name, "type": typ}
                    for name, typ in node.config.fields
                ],
                "entity": node.config.entity,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, ValidatorConfig):
            # Rules serialize in the canonical [field, constraint] pair form
            # the parser accepts.
            entry["config"] = {
                "name": node.config.name,
                "entity": node.config.entity,
                "rules": [
                    [field, constraint]
                    for field, constraint in node.config.rules
                ],
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, SearchIndexConfig):
            entry["config"] = {
                "name": node.config.name,
                "entity": node.config.entity,
                "fields": list(node.config.fields),
                "engine": node.config.engine,
                "boost": dict(node.config.boost or {}),
                "fuzzy": node.config.fuzzy,
                "suggestions": node.config.suggestions,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, FileUploadConfig):
            entry["config"] = {
                "name": node.config.name,
                "route": node.config.route,
                "storage": node.config.storage,
                "maxSize": node.config.max_size,
                "allowedTypes": list(node.config.allowed_types),
                "directory": node.config.directory,
                "generateThumbnails": node.config.generate_thumbnails,
                "thumbnailSizes": [
                    {"width": t.width, "height": t.height, "fit": t.fit}
                    for t in node.config.thumbnail_sizes
                ],
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, AuditLogConfig):
            entry["config"] = {
                "name": node.config.name,
                "entity": node.config.entity,
                "operations": list(node.config.operations),
                "captureFields": list(node.config.capture_fields),
                "excludeFields": list(node.config.exclude_fields),
                "captureRequestMeta": node.config.capture_request_meta,
                "retentionDays": node.config.retention_days,
                "enabled": node.config.enabled,
                "description": node.config.description,
            }
        elif isinstance(node.config, ApiKeyGroupConfig):
            entry["config"] = {
                "name": node.config.name,
                "description": node.config.description,
                "keyPrefix": node.config.key_prefix,
                "keyHeader": node.config.key_header,
                "rateLimit": node.config.rate_limit or None,
                "permissions": [
                    {
                        "resource": perm.resource,
                        "actions": list(perm.actions),
                        "scopes": list(perm.scopes),
                    }
                    for perm in node.config.permissions
                ],
                "expiresAt": node.config.expires_at or None,
                "enabled": node.config.enabled,
            }
        elif isinstance(node.config, EmailTemplateConfig):
            entry["config"] = {
                "name": node.config.name,
                "subject": node.config.subject,
                "from": node.config.from_email,
                "replyTo": node.config.reply_to or None,
                "htmlTemplate": node.config.html_template,
                "textTemplate": node.config.text_template or None,
                "variables": [
                    {
                        "name": var.name,
                        "type": var.type,
                        "required": var.required,
                        "defaultValue": var.default,
                    }
                    for var in node.config.variables
                ],
                "triggers": list(node.config.triggers),
                "enabled": node.config.enabled,
                "description": node.config.description,
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
        version = int(data.get("version", 1))
        raw_nodes = data.get("nodes", [])
        raw_edges = data.get("edges", [])
        nodes: list[GraphNode] = []
        for raw in raw_nodes:
            pos = Position(x=float(raw["position"]["x"]), y=float(raw["position"]["y"]))
            kind = str(raw["kind"])
            if kind not in KNOWN_KINDS:
                return Err(GraphValidationError(f"unknown node kind {kind!r}"))
            config: (
                AppSettingsConfig
                | EntityConfig
                | RouteConfig
                | MiddlewareConfig
                | CronConfig
                | WebhookConfig
                | JobConfig
                | ServiceConfig
                | SeederConfig
                | ExceptionFilterConfig
                | ErrorConfig
                | CacheConfig
                | GraphQLConfig
                | HealthConfig
                | EventConfig
                | EventHandlerConfig
                | CqrsMessageConfig
                | ProjectionConfig
                | MetricConfig
                | SagaConfig
                | ApiClientConfig
                | StorageDriverConfig
                | ChannelConfig
                | FeatureFlagConfig
                | AuthConfig
                | RoleConfig
                | RateLimitConfig
                | ContractConfig
                | ValidatorConfig
                | SearchIndexConfig
                | FileUploadConfig
                | AuditLogConfig
                | ApiKeyGroupConfig
                | EmailTemplateConfig
                | None
            ) = None
            raw_cfg = raw.get("config")
            if kind == "app_settings":
                raw_features = raw_cfg.get("features") or {}
                if isinstance(raw_features, dict):
                    features = frozenset(
                        str(k) for k, v in raw_features.items() if bool(v)
                    )
                elif isinstance(raw_features, (list, tuple, set, frozenset)):
                    features = frozenset(str(k) for k in raw_features)
                else:
                    features = frozenset()
                config = AppSettingsConfig(
                    app_name=str(raw_cfg["app_name"]),
                    port=int(raw_cfg["port"]),
                    db=str(raw_cfg["db"]),
                    structure=normalize_structure(
                        str(raw_cfg.get("structure", "minimal"))
                    ),
                    features=features,
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
            elif kind == "middleware":
                if raw_cfg is None:
                    raw_cfg = {}
                config = MiddlewareConfig(
                    name=str(raw_cfg.get("name", "middleware")),
                    type=str(raw_cfg.get("type", "custom")),
                    order=int(raw_cfg.get("order", 100)),
                )
            elif kind == "cron":
                if raw_cfg is None:
                    raw_cfg = {}
                config = CronConfig(
                    name=str(raw_cfg.get("name", "scheduled_task")),
                    schedule=str(raw_cfg.get("schedule", "0 * * * *")),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "webhook":
                if raw_cfg is None:
                    raw_cfg = {}
                name = str(raw_cfg.get("name", "webhook"))
                default_env = (
                    "WEBHOOK_"
                    + "".join(c.upper() if c.isalnum() else "_" for c in name)
                    + "_SECRET"
                )
                config = WebhookConfig(
                    name=name,
                    path=str(raw_cfg.get("path", "") or f"/webhooks/{name}"),
                    verify_signature=bool(raw_cfg.get("verify_signature", True)),
                    secret_env=str(raw_cfg.get("secret_env", "") or default_env),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "job":
                if raw_cfg is None:
                    raw_cfg = {}
                config = JobConfig(
                    name=str(raw_cfg.get("name", "job")),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "realtime_channel":
                if raw_cfg is None:
                    raw_cfg = {}
                ws_name = str(raw_cfg.get("name", "channel"))
                config = ChannelConfig(
                    name=ws_name,
                    path=str(raw_cfg.get("path", "") or f"/ws/{ws_name}"),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "service":
                if raw_cfg is None:
                    raw_cfg = {}
                config = ServiceConfig(
                    name=str(raw_cfg.get("name", "service")),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "seeder":
                if raw_cfg is None:
                    raw_cfg = {}
                config = SeederConfig(
                    name=str(raw_cfg.get("name", "seeder")),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "exception_filter":
                if raw_cfg is None:
                    raw_cfg = {}
                config = ExceptionFilterConfig(
                    name=str(raw_cfg.get("name", "filter")),
                    exception_type=str(
                        raw_cfg.get("exception_type")
                        or raw_cfg.get("exceptionType")
                        or "ValueError"
                    ),
                    status_code=int(
                        raw_cfg.get("status_code")
                        or raw_cfg.get("statusCode")
                        or 400
                    ),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "error":
                if raw_cfg is None:
                    raw_cfg = {}
                config = ErrorConfig(
                    name=str(raw_cfg.get("name", "error")),
                    status_code=int(
                        raw_cfg.get("status_code")
                        or raw_cfg.get("statusCode")
                        or 400
                    ),
                    error_code=str(
                        raw_cfg.get("error_code")
                        or raw_cfg.get("errorCode")
                        or ""
                    ),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "cache":
                if raw_cfg is None:
                    raw_cfg = {}
                config = CacheConfig(
                    name=str(raw_cfg.get("name", "cache")),
                    ttl=_ttl_seconds(raw_cfg.get("ttl", 300)),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "graphql":
                if raw_cfg is None:
                    raw_cfg = {}
                config = GraphQLConfig(
                    name=str(raw_cfg.get("name", "graphql")),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "health":
                if raw_cfg is None:
                    raw_cfg = {}
                config = HealthConfig(
                    name=str(raw_cfg.get("name", "health")),
                    critical=bool(raw_cfg.get("critical", True)),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "event":
                if raw_cfg is None:
                    raw_cfg = {}
                payload = _event_payload(raw_cfg)
                config = EventConfig(
                    name=str(raw_cfg.get("name", "event")),
                    payload=tuple(payload),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "event_handler":
                if raw_cfg is None:
                    raw_cfg = {}
                config = EventHandlerConfig(
                    name=str(raw_cfg.get("name", "handler")),
                    event=str(raw_cfg.get("event", "")),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind in ("command", "query"):
                if raw_cfg is None:
                    raw_cfg = {}
                side = str(raw_cfg.get("side", kind))
                fields_raw = raw_cfg.get("fields") or []
                if not isinstance(fields_raw, list):
                    fields_raw = []
                config = CqrsMessageConfig(
                    name=str(raw_cfg.get("name", kind)),
                    side=side if side in ("command", "query") else kind,
                    entity=str(raw_cfg.get("entity", "")),
                    fields=tuple(
                        (str(f.get("name", "")), str(f.get("type", "str")))
                        for f in fields_raw
                        if isinstance(f, dict) and f.get("name")
                    ),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "projection":
                if raw_cfg is None:
                    raw_cfg = {}
                events_raw = raw_cfg.get("events") or []
                if not isinstance(events_raw, list):
                    events_raw = []
                config = ProjectionConfig(
                    name=str(raw_cfg.get("name", "projection")),
                    events=tuple(str(e) for e in events_raw if isinstance(e, str)),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "metric":
                if raw_cfg is None:
                    raw_cfg = {}
                config = MetricConfig(
                    name=str(raw_cfg.get("name", "metric")),
                    unit=str(raw_cfg.get("unit", "count")),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "saga":
                if raw_cfg is None:
                    raw_cfg = {}
                config = SagaConfig(
                    name=str(raw_cfg.get("name", "saga")),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "api_client":
                if raw_cfg is None:
                    raw_cfg = {}
                config = ApiClientConfig(
                    name=str(raw_cfg.get("name", "api_client")),
                    base_url=str(
                        raw_cfg.get("base_url") or raw_cfg.get("baseUrl") or "https://api.example.com"
                    ),
                    auth_type=str(
                        raw_cfg.get("auth_type") or raw_cfg.get("authType") or "apikey"
                    ),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "storage_driver":
                if raw_cfg is None:
                    raw_cfg = {}
                config = StorageDriverConfig(
                    name=str(raw_cfg.get("name", "storage_driver")),
                    driver_type=str(
                        raw_cfg.get("driver_type") or raw_cfg.get("driverType") or "custom"
                    ),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "feature_flag":
                if raw_cfg is None:
                    raw_cfg = {}
                config = FeatureFlagConfig(
                    name=str(raw_cfg.get("name", "flag")),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "auth":
                if raw_cfg is None:
                    raw_cfg = {}
                config = AuthConfig(
                    name=str(raw_cfg.get("name", "auth")),
                    provider=str(raw_cfg.get("provider", "jwt")),
                    login_path=str(raw_cfg.get("login_path") or raw_cfg.get("loginPath") or "/auth/login"),
                    refresh_token=bool(
                        raw_cfg.get("refresh_token", raw_cfg.get("refreshToken", True))
                    ),
                    token_expiry=str(
                        raw_cfg.get("token_expiry") or raw_cfg.get("tokenExpiry") or "30m"
                    ),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "role":
                if raw_cfg is None:
                    raw_cfg = {}
                config = RoleConfig(
                    name=str(raw_cfg.get("name", "role")),
                    permissions=_flatten_permissions(raw_cfg.get("permissions")),
                    inherits=tuple(
                        str(r)
                        for r in (raw_cfg.get("inherits") or [])
                        if isinstance(r, str)
                    ),
                    is_default=bool(
                        raw_cfg.get("is_default", raw_cfg.get("isDefault", False))
                    ),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "rate_limit":
                if raw_cfg is None:
                    raw_cfg = {}
                config = RateLimitConfig(
                    name=str(raw_cfg.get("name", "rate_limit")),
                    strategy=str(raw_cfg.get("strategy", "fixed_window")),
                    window_seconds=_ttl_seconds(
                        raw_cfg.get("window_seconds") or raw_cfg.get("window") or 60
                    ),
                    max_requests=int(
                        raw_cfg.get("max_requests") or raw_cfg.get("maxRequests") or 60
                    ),
                    key_by=str(raw_cfg.get("key_by") or raw_cfg.get("keyBy") or "ip"),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "search_index":
                if raw_cfg is None:
                    raw_cfg = {}
                fields_raw = raw_cfg.get("fields") or []
                if not isinstance(fields_raw, list):
                    fields_raw = []
                boost_raw = raw_cfg.get("boost") or {}
                boost: dict[str, float] = {}
                if isinstance(boost_raw, dict):
                    for key, value in boost_raw.items():
                        try:
                            boost[str(key)] = float(value)  # type: ignore[arg-type]
                        except (TypeError, ValueError):
                            continue
                engine = str(raw_cfg.get("engine", "fts"))
                config = SearchIndexConfig(
                    name=str(raw_cfg.get("name", "search")),
                    entity=str(raw_cfg.get("entity", "")),
                    fields=tuple(str(f) for f in fields_raw if f),
                    engine=engine
                    if engine in ("like", "fts", "meilisearch", "elasticsearch")
                    else "fts",
                    boost=boost,
                    fuzzy=bool(raw_cfg.get("fuzzy", False)),
                    suggestions=bool(raw_cfg.get("suggestions", False)),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "file_upload":
                if raw_cfg is None:
                    raw_cfg = {}
                types_raw = (
                    raw_cfg.get("allowed_types")
                    or raw_cfg.get("allowedTypes")
                    or []
                )
                if not isinstance(types_raw, list):
                    types_raw = []
                sizes_raw = (
                    raw_cfg.get("thumbnail_sizes")
                    or raw_cfg.get("thumbnailSizes")
                    or []
                )
                thumb_sizes: list[ThumbnailSize] = []
                if isinstance(sizes_raw, list):
                    for item in sizes_raw:
                        if not isinstance(item, dict):
                            continue
                        try:
                            thumb_sizes.append(
                                ThumbnailSize(
                                    width=int(item.get("width", 256)),
                                    height=int(item.get("height", 256)),
                                    fit=str(item.get("fit", "cover")),
                                )
                            )
                        except (TypeError, ValueError):
                            continue
                config = FileUploadConfig(
                    name=str(raw_cfg.get("name", "upload")),
                    route=str(raw_cfg.get("route", "")),
                    storage=str(raw_cfg.get("storage", "local")),
                    max_size=str(
                        raw_cfg.get("max_size")
                        or raw_cfg.get("maxSize")
                        or "5MB"
                    ),
                    allowed_types=tuple(str(t) for t in types_raw if t),
                    directory=str(raw_cfg.get("directory", "uploads")),
                    generate_thumbnails=bool(
                        raw_cfg.get("generate_thumbnails")
                        if raw_cfg.get("generate_thumbnails") is not None
                        else raw_cfg.get("generateThumbnails", False)
                    ),
                    thumbnail_sizes=tuple(thumb_sizes),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "validator":
                if raw_cfg is None:
                    raw_cfg = {}
                rules_raw = raw_cfg.get("rules") or []
                if not isinstance(rules_raw, list):
                    rules_raw = []
                rules: list[tuple[str, str]] = []
                for entry in rules_raw:
                    if isinstance(entry, dict):
                        field = str(entry.get("field", ""))
                        # Legacy screen-era shape carried a rule list per
                        # field (plus message/async); join into one expr.
                        expr_raw = entry.get("constraint") or entry.get("rule")
                        if expr_raw is None:
                            legacy = entry.get("rules") or []
                            if isinstance(legacy, (list, tuple)):
                                expr_raw = ",".join(str(r) for r in legacy)
                            else:
                                expr_raw = str(legacy)
                        if field:
                            rules.append((field, str(expr_raw)))
                    elif (
                        isinstance(entry, (list, tuple)) and len(entry) == 2
                    ):
                        # Canonical serialized pair form: [field, constraint].
                        rules.append((str(entry[0]), str(entry[1])))
                config = ValidatorConfig(
                    name=str(raw_cfg.get("name", "validator")),
                    entity=str(raw_cfg.get("entity", "")),
                    rules=tuple(rules),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "contract":
                if raw_cfg is None:
                    raw_cfg = {}
                fields_raw = raw_cfg.get("fields") or []
                if not isinstance(fields_raw, list):
                    fields_raw = []
                direction = str(raw_cfg.get("direction", "both"))
                config = ContractConfig(
                    name=str(raw_cfg.get("name", "contract")),
                    direction=(
                        direction
                        if direction in ("request", "response", "both")
                        else "both"
                    ),
                    fields=tuple(
                        (str(f.get("name", "")), str(f.get("type", "str")))
                        for f in fields_raw
                        if isinstance(f, dict) and f.get("name")
                    ),
                    entity=str(raw_cfg.get("entity", "")),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "audit_log":
                if raw_cfg is None:
                    raw_cfg = {}
                ops_raw = raw_cfg.get("operations")
                if ops_raw is None:
                    ops_raw = ["create", "update", "delete"]
                if not isinstance(ops_raw, list):
                    ops_raw = []
                excl_raw = raw_cfg.get("excludeFields")
                if excl_raw is None:
                    excl_raw = ["password", "token"]
                if not isinstance(excl_raw, list):
                    excl_raw = []
                cap_raw = raw_cfg.get("captureFields") or []
                if not isinstance(cap_raw, list):
                    cap_raw = []
                config = AuditLogConfig(
                    name=str(raw_cfg.get("name", "audit")),
                    entity=str(raw_cfg.get("entity", "")),
                    operations=tuple(
                        str(op) for op in ops_raw if isinstance(op, str)
                    ),
                    capture_fields=tuple(
                        str(f) for f in cap_raw if isinstance(f, str)
                    ),
                    exclude_fields=tuple(
                        str(f) for f in excl_raw if isinstance(f, str)
                    ),
                    capture_request_meta=bool(
                        raw_cfg.get("captureRequestMeta", False)
                    ),
                    retention_days=int(raw_cfg.get("retentionDays", 90)),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            elif kind == "api_key_group":
                if raw_cfg is None:
                    raw_cfg = {}
                perms_raw = raw_cfg.get("permissions") or []
                if not isinstance(perms_raw, list):
                    perms_raw = []
                permissions: list[ApiKeyPermission] = []
                for entry in perms_raw:
                    if not isinstance(entry, dict):
                        continue
                    actions_raw = entry.get("actions") or []
                    scopes_raw = entry.get("scopes") or []
                    if not isinstance(actions_raw, list):
                        actions_raw = []
                    if not isinstance(scopes_raw, list):
                        scopes_raw = []
                    permissions.append(
                        ApiKeyPermission(
                            resource=str(entry.get("resource", "")),
                            actions=tuple(
                                str(a) for a in actions_raw if isinstance(a, str)
                            ),
                            scopes=tuple(
                                str(s) for s in scopes_raw if isinstance(s, str)
                            ),
                        )
                    )
                config = ApiKeyGroupConfig(
                    name=str(raw_cfg.get("name", "partner_api")),
                    description=str(raw_cfg.get("description", "")),
                    key_prefix=str(
                        raw_cfg.get("keyPrefix")
                        or raw_cfg.get("key_prefix")
                        or "pk_live_"
                    ),
                    key_header=str(
                        raw_cfg.get("keyHeader")
                        or raw_cfg.get("key_header")
                        or "X-API-Key"
                    ),
                    rate_limit=str(
                        raw_cfg.get("rateLimit") or raw_cfg.get("rate_limit") or ""
                    ),
                    permissions=tuple(permissions),
                    expires_at=str(
                        raw_cfg.get("expiresAt") or raw_cfg.get("expires_at") or ""
                    ),
                    enabled=bool(raw_cfg.get("enabled", True)),
                )
            elif kind == "email_template":
                if raw_cfg is None:
                    raw_cfg = {}
                vars_raw = raw_cfg.get("variables") or []
                if not isinstance(vars_raw, list):
                    vars_raw = []
                variables: list[EmailVariable] = []
                for entry in vars_raw:
                    if not isinstance(entry, dict):
                        continue
                    default_raw = entry.get("defaultValue")
                    variables.append(
                        EmailVariable(
                            name=str(entry.get("name", "")),
                            type=str(entry.get("type", "str")),
                            required=bool(entry.get("required", True)),
                            default=(
                                str(default_raw)
                                if default_raw is not None
                                else None
                            ),
                        )
                    )
                triggers_raw = raw_cfg.get("triggers") or []
                if not isinstance(triggers_raw, list):
                    triggers_raw = []
                config = EmailTemplateConfig(
                    name=str(raw_cfg.get("name", "welcome_email")),
                    subject=str(raw_cfg.get("subject", "")),
                    from_email=str(
                        raw_cfg.get("from") or raw_cfg.get("from_email") or ""
                    ),
                    reply_to=str(
                        raw_cfg.get("replyTo") or raw_cfg.get("reply_to") or ""
                    ),
                    html_template=str(
                        raw_cfg.get("htmlTemplate")
                        or raw_cfg.get("html_template")
                        or ""
                    ),
                    text_template=str(
                        raw_cfg.get("textTemplate")
                        or raw_cfg.get("text_template")
                        or ""
                    ),
                    variables=tuple(variables),
                    triggers=tuple(
                        str(t) for t in triggers_raw if isinstance(t, str)
                    ),
                    enabled=bool(raw_cfg.get("enabled", True)),
                    description=str(raw_cfg.get("description", "")),
                )
            nodes.append(
                GraphNode(id=str(raw["id"]), kind=kind, position=pos, config=config)
            )
        edges = [
            GraphEdge(
                id=str(e["id"]),
                src=str(e.get("src") or e.get("source", "")),
                dst=str(e.get("dst") or e.get("target", "")),
            )
            for e in raw_edges
        ]
        return Ok(
            GraphDocument(version=version, nodes=tuple(nodes), edges=tuple(edges))
        )
    except (KeyError, TypeError, ValueError) as exc:
        return Err(GraphValidationError(f"malformed graph document: {exc}"))
