"""Node-kind palette: all 23 node kinds, field types, ops, edge rules, ports."""

from __future__ import annotations

import keyword

# ── Node Kinds ────────────────────────────────────────────────────────

KIND_APP_SETTINGS = "app_settings"
KIND_ENTITY = "entity"
KIND_FIELD = "field"
KIND_ROUTE = "route"
KIND_AUTH = "auth"
KIND_ROLE = "role"
KIND_MIDDLEWARE = "middleware"
KIND_VALIDATOR = "validator"
KIND_JOB = "job"
KIND_EVENT = "event"
KIND_CACHE = "cache"
KIND_SEARCH_INDEX = "search_index"
KIND_WEBHOOK = "webhook"
KIND_REALTIME_CHANNEL = "realtime_channel"
KIND_FILE_UPLOAD = "file_upload"
KIND_EMAIL_TEMPLATE = "email_template"
KIND_PAGE = "page"
KIND_COMPONENT = "component"
KIND_DASHBOARD = "dashboard"
KIND_API_KEY_GROUP = "api_key_group"
KIND_AUDIT_LOG = "audit_log"
KIND_RATE_LIMIT = "rate_limit"
KIND_CRON = "cron"
KIND_SERVICE = "service"
KIND_SEEDER = "seeder"
KIND_EXCEPTION_FILTER = "exception_filter"
KIND_ERROR = "error"
KIND_GRAPHQL = "graphql"
KIND_HEALTH = "health"
KIND_EVENT_HANDLER = "event_handler"
KIND_COMMAND = "command"
KIND_QUERY = "query"
KIND_PROJECTION = "projection"
KIND_METRIC = "metric"
KIND_SAGA = "saga"
KIND_API_CLIENT = "api_client"
KIND_STORAGE_DRIVER = "storage_driver"
KIND_FEATURE_FLAG = "feature_flag"
KIND_CONTRACT = "contract"

KNOWN_KINDS: frozenset[str] = frozenset(
    {
        KIND_APP_SETTINGS, KIND_ENTITY, KIND_FIELD, KIND_ROUTE,
        KIND_AUTH, KIND_ROLE, KIND_MIDDLEWARE, KIND_VALIDATOR,
        KIND_JOB, KIND_EVENT, KIND_CACHE, KIND_SEARCH_INDEX,
        KIND_WEBHOOK, KIND_REALTIME_CHANNEL, KIND_FILE_UPLOAD,
        KIND_EMAIL_TEMPLATE, KIND_PAGE, KIND_COMPONENT,
        KIND_DASHBOARD, KIND_API_KEY_GROUP, KIND_AUDIT_LOG,
        KIND_RATE_LIMIT, KIND_CRON, KIND_SERVICE, KIND_SEEDER,
        KIND_EXCEPTION_FILTER, KIND_ERROR, KIND_GRAPHQL, KIND_HEALTH,
        KIND_EVENT_HANDLER, KIND_COMMAND, KIND_QUERY,
        KIND_PROJECTION, KIND_METRIC, KIND_SAGA, KIND_API_CLIENT, KIND_STORAGE_DRIVER,
        KIND_FEATURE_FLAG, KIND_CONTRACT,
    }
)

# ── Field Types ───────────────────────────────────────────────────────

FIELD_TYPES: frozenset[str] = frozenset(
    {
        "str", "int", "float", "bool", "datetime", "date", "time",
        "uuid", "text", "json", "bytes", "enum", "decimal",
        "ipv4", "ipv6", "email", "url", "phone", "filename", "filepath",
    }
)

# ── CRUD Operations ───────────────────────────────────────────────────

ENTITY_OPS: frozenset[str] = frozenset({"create", "get", "list", "update", "delete"})

# ── Database & Structure ──────────────────────────────────────────────

DB_PRESETS: frozenset[str] = frozenset({"sqlite", "postgres"})

# Project structures mirror the framework's canonical vocabulary in
# ``lexigram.cli.layout`` (minimal / structured / modular). Keeping the same
# names means a generated project's ``[tool.lexigram] structure`` is directly
# understood by ``lexigram gen`` inside that project.
STRUCTURE_MINIMAL = "minimal"
STRUCTURE_STRUCTURED = "structured"
STRUCTURE_MODULAR = "modular"

PROJECT_STRUCTURES: dict[str, str] = {
    STRUCTURE_MINIMAL: (
        "Single app package (src/<app>) — components nested inside it"
    ),
    STRUCTURE_STRUCTURED: (
        "Generator-native layout — app composition root plus sibling "
        "src/ component packages"
    ),
    STRUCTURE_MODULAR: (
        "Bounded contexts — src/<app>/modules/<feature>, shared/, infrastructure/"
    ),
}

# Legacy playground names, mapped onto the canonical structures so graphs
# saved before the alignment still load and validate.
LEGACY_STRUCTURES: dict[str, str] = {
    "standard": STRUCTURE_MINIMAL,
    "service_layered": STRUCTURE_STRUCTURED,
    "modular_monolith": STRUCTURE_MODULAR,
}


def normalize_structure(name: str) -> str:
    """Return the canonical structure for *name*, mapping legacy spellings.

    Unknown names are passed through untouched so validation can flag them
    as ``unknown-structure`` instead of silently defaulting.
    """
    return LEGACY_STRUCTURES.get(name, name)

# ── Auth Providers ────────────────────────────────────────────────────

AUTH_PROVIDERS: frozenset[str] = frozenset(
    {"jwt", "session", "api_key", "oauth2", "basic", "custom"}
)

# ── Middleware Types ───────────────────────────────────────────────────

MIDDLEWARE_TYPES: frozenset[str] = frozenset(
    {"cors", "logging", "compression", "security_headers", "request_id", "timing", "error_handler", "custom"}
)

# ── Cache Backends ────────────────────────────────────────────────────

CACHE_BACKENDS: frozenset[str] = frozenset({"memory", "redis", "database"})

# ── Search Engines ────────────────────────────────────────────────────

SEARCH_ENGINES: frozenset[str] = frozenset({"like", "fts", "meilisearch", "elasticsearch"})

# ── Storage Backends ──────────────────────────────────────────────────

STORAGE_BACKENDS: frozenset[str] = frozenset({"local", "s3", "gcs", "azure_blob"})

# ── Rate Limit Strategies ─────────────────────────────────────────────

RATE_LIMIT_STRATEGIES: frozenset[str] = frozenset(
    {"fixed_window", "sliding_window", "token_bucket"}
)

# ── Component Types ───────────────────────────────────────────────────

COMPONENT_TYPES: frozenset[str] = frozenset(
    {
        "data_table", "form", "card", "list", "detail_view",
        "chart", "stat_card", "search_bar", "filter_panel", "modal",
        "tabs", "sidebar", "header", "footer", "richtext",
        "code_block", "custom",
    }
)

# ── Port Types ────────────────────────────────────────────────────────

PORT_TYPE_ENTITY_REF = "entity_ref"
PORT_TYPE_ROUTE_REF = "route_ref"
PORT_TYPE_EVENT_REF = "event_ref"
PORT_TYPE_CONFIG_REF = "config_ref"
PORT_TYPE_DATA_REF = "data_ref"

PORT_TYPES: frozenset[str] = frozenset(
    {PORT_TYPE_ENTITY_REF, PORT_TYPE_ROUTE_REF, PORT_TYPE_EVENT_REF, PORT_TYPE_CONFIG_REF, PORT_TYPE_DATA_REF}
)

# ── Port Definitions per Node Kind ────────────────────────────────────
# Each entry: {side: "left"|"right"|"top"|"bottom", type: PortType, label: str, max: int|None}

NODE_PORTS: dict[str, dict[str, list[dict[str, object]]]] = {
    KIND_APP_SETTINGS: {
        "inputs": [],
        "outputs": [
            {"id": "output_config", "side": "right", "type": PORT_TYPE_CONFIG_REF, "label": "Config", "max": None},
        ],
    },
    KIND_ENTITY: {
        "inputs": [
            {"id": "input_route", "side": "left", "type": PORT_TYPE_ROUTE_REF, "label": "Routes", "max": None},
        ],
        "outputs": [
            {"id": "output_entity", "side": "right", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": None},
            {"id": "output_events", "side": "bottom", "type": PORT_TYPE_EVENT_REF, "label": "Events", "max": None},
        ],
    },
    KIND_FIELD: {"inputs": [], "outputs": []},
    KIND_ROUTE: {
        "inputs": [],
        "outputs": [
            {"id": "output_entity", "side": "right", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": 1},
            {"id": "output_middleware", "side": "bottom", "type": PORT_TYPE_CONFIG_REF, "label": "Middleware", "max": None},
        ],
    },
    KIND_MIDDLEWARE: {
        "inputs": [
            {"id": "input_config", "side": "left", "type": PORT_TYPE_CONFIG_REF, "label": "Config", "max": None},
        ],
        "outputs": [
            {"id": "output_config", "side": "right", "type": PORT_TYPE_CONFIG_REF, "label": "Config", "max": None},
        ],
    },
    KIND_VALIDATOR: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": 1},
        ],
        "outputs": [],
    },
    KIND_AUTH: {
        "inputs": [],
        "outputs": [
            {"id": "output_auth", "side": "right", "type": PORT_TYPE_CONFIG_REF, "label": "Auth", "max": None},
        ],
    },
    KIND_ROLE: {
        "inputs": [
            {"id": "input_auth", "side": "left", "type": PORT_TYPE_CONFIG_REF, "label": "Auth", "max": 1},
        ],
        "outputs": [
            {"id": "output_role", "side": "right", "type": PORT_TYPE_CONFIG_REF, "label": "Role", "max": None},
        ],
    },
    KIND_JOB: {
        "inputs": [
            {"id": "input_trigger", "side": "left", "type": PORT_TYPE_EVENT_REF, "label": "Trigger", "max": None},
        ],
        "outputs": [
            {"id": "output_result", "side": "right", "type": PORT_TYPE_DATA_REF, "label": "Result", "max": None},
        ],
    },
    KIND_EVENT: {
        "inputs": [
            {"id": "input_producer", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Producer", "max": None},
        ],
        "outputs": [
            {"id": "output_consumer", "side": "right", "type": PORT_TYPE_EVENT_REF, "label": "Consumers", "max": None},
        ],
    },
    KIND_CACHE: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": None},
        ],
        "outputs": [],
    },
    KIND_GRAPHQL: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": None},
        ],
        "outputs": [],
    },
    KIND_HEALTH: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": None},
        ],
        "outputs": [],
    },
    KIND_EVENT_HANDLER: {
        "inputs": [
            {"id": "input_event", "side": "left", "type": PORT_TYPE_EVENT_REF, "label": "Event", "max": 1},
        ],
        "outputs": [],
    },
    KIND_COMMAND: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Aggregate", "max": 1},
        ],
        "outputs": [],
    },
    KIND_QUERY: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Read model", "max": 1},
        ],
        "outputs": [],
    },
    KIND_PROJECTION: {
        "inputs": [
            {"id": "input_events", "side": "left", "type": PORT_TYPE_EVENT_REF, "label": "Events", "max": None},
        ],
        "outputs": [],
    },
    KIND_METRIC: {
        "inputs": [],
        "outputs": [],
    },
    KIND_SAGA: {
        "inputs": [
            {"id": "input_events", "side": "left", "type": PORT_TYPE_EVENT_REF, "label": "Events", "max": None},
        ],
        "outputs": [],
    },
    KIND_API_CLIENT: {
        "inputs": [],
        "outputs": [],
    },
    KIND_STORAGE_DRIVER: {
        "inputs": [
            {"id": "input_upload", "side": "left", "type": PORT_TYPE_DATA_REF, "label": "Uploads", "max": None},
        ],
        "outputs": [],
    },
    KIND_SEARCH_INDEX: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": 1},
        ],
        "outputs": [],
    },
    KIND_WEBHOOK: {
        "inputs": [
            {"id": "input_event", "side": "left", "type": PORT_TYPE_EVENT_REF, "label": "Event", "max": 1},
        ],
        "outputs": [],
    },
    KIND_REALTIME_CHANNEL: {
        "inputs": [
            {"id": "input_event", "side": "left", "type": PORT_TYPE_EVENT_REF, "label": "Event", "max": None},
        ],
        "outputs": [],
    },
    KIND_FILE_UPLOAD: {
        "inputs": [
            {"id": "input_route", "side": "left", "type": PORT_TYPE_ROUTE_REF, "label": "Route", "max": 1},
        ],
        "outputs": [
            {"id": "output_storage", "side": "right", "type": PORT_TYPE_DATA_REF, "label": "Driver", "max": 1},
        ],
    },
    KIND_EMAIL_TEMPLATE: {
        "inputs": [
            {"id": "input_event", "side": "left", "type": PORT_TYPE_EVENT_REF, "label": "Trigger", "max": None},
        ],
        "outputs": [],
    },
    KIND_PAGE: {
        "inputs": [],
        "outputs": [
            {"id": "output_component", "side": "right", "type": PORT_TYPE_CONFIG_REF, "label": "Components", "max": None},
            {"id": "output_route", "side": "bottom", "type": PORT_TYPE_ROUTE_REF, "label": "Routes", "max": None},
        ],
    },
    KIND_COMPONENT: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Data", "max": 1},
        ],
        "outputs": [],
    },
    KIND_DASHBOARD: {
        "inputs": [],
        "outputs": [
            {"id": "output_widget", "side": "right", "type": PORT_TYPE_CONFIG_REF, "label": "Widgets", "max": None},
        ],
    },
    KIND_API_KEY_GROUP: {
        "inputs": [],
        "outputs": [
            {"id": "output_config", "side": "right", "type": PORT_TYPE_CONFIG_REF, "label": "Config", "max": None},
        ],
    },
    KIND_AUDIT_LOG: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": 1},
        ],
        "outputs": [],
    },
    KIND_RATE_LIMIT: {
        "inputs": [],
        "outputs": [
            {"id": "output_config", "side": "right", "type": PORT_TYPE_CONFIG_REF, "label": "Config", "max": None},
        ],
    },
    KIND_CRON: {
        "inputs": [],
        "outputs": [
            {"id": "output_trigger", "side": "right", "type": PORT_TYPE_EVENT_REF, "label": "Trigger", "max": None},
        ],
    },
    KIND_SERVICE: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": 1},
        ],
        "outputs": [],
    },
    KIND_SEEDER: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": 1},
        ],
        "outputs": [],
    },
    KIND_EXCEPTION_FILTER: {
        "inputs": [
            {"id": "input_config", "side": "left", "type": PORT_TYPE_CONFIG_REF, "label": "Applies to", "max": None},
        ],
        "outputs": [
            {"id": "output_config", "side": "right", "type": PORT_TYPE_CONFIG_REF, "label": "Filters", "max": None},
        ],
    },
    KIND_ERROR: {
        "inputs": [
            {"id": "input_entity", "side": "left", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": 1},
        ],
        "outputs": [],
    },
    KIND_FEATURE_FLAG: {
        "inputs": [
            {"id": "input_policy", "side": "left", "type": PORT_TYPE_CONFIG_REF, "label": "Routes", "max": None},
        ],
        "outputs": [],
    },
    KIND_CONTRACT: {
        "inputs": [
            {"id": "input_config", "side": "left", "type": PORT_TYPE_CONFIG_REF, "label": "Routes", "max": None},
        ],
        "outputs": [
            {"id": "output_entity", "side": "right", "type": PORT_TYPE_ENTITY_REF, "label": "Entity", "max": 1},
        ],
    },
}

# ── Edge Validation Rules ─────────────────────────────────────────────

ALLOWED_EDGES: frozenset[tuple[str, str]] = frozenset(
    {
        # Core CRUD
        (KIND_ROUTE, KIND_ENTITY),
        (KIND_ENTITY, KIND_ENTITY),
        # Service layer (entity -> its business-logic service)
        (KIND_ENTITY, KIND_SERVICE),
        # Seed data (entity -> its idempotent seeder)
        (KIND_ENTITY, KIND_SEEDER),
        # Domain HTTP errors (entity -> its <Name>Error class)
        (KIND_ENTITY, KIND_ERROR),
        # Validation
        (KIND_ENTITY, KIND_VALIDATOR),
        # Auth
        (KIND_ROUTE, KIND_AUTH),
        (KIND_ROUTE, KIND_ROLE),
        (KIND_ROLE, KIND_AUTH),
        # Middleware
        (KIND_ENTITY, KIND_MIDDLEWARE),
        (KIND_ROUTE, KIND_MIDDLEWARE),
        # Rate Limiting
        (KIND_ROUTE, KIND_RATE_LIMIT),
        # Exception filters (global; edges annotate scope)
        (KIND_ROUTE, KIND_EXCEPTION_FILTER),
        (KIND_EXCEPTION_FILTER, KIND_EXCEPTION_FILTER),
        # Events & Jobs
        (KIND_ENTITY, KIND_EVENT),
        # CQRS write/read intents against an aggregate
        (KIND_ENTITY, KIND_COMMAND),
        (KIND_ENTITY, KIND_QUERY),
        # Event handlers subscribe to a domain event
        (KIND_EVENT, KIND_EVENT_HANDLER),
        # Projections consume domain events to build read models
        (KIND_EVENT, KIND_PROJECTION),
        (KIND_EVENT, KIND_SAGA),
        (KIND_EVENT, KIND_JOB),
        (KIND_CRON, KIND_JOB),
        (KIND_CRON, KIND_EVENT),
        # Inbound webhook triggers fan out to jobs and events
        (KIND_WEBHOOK, KIND_JOB),
        (KIND_WEBHOOK, KIND_EVENT),
        # Realtime channels broadcast from triggers / events / jobs
        (KIND_WEBHOOK, KIND_REALTIME_CHANNEL),
        (KIND_EVENT, KIND_REALTIME_CHANNEL),
        (KIND_JOB, KIND_REALTIME_CHANNEL),
        (KIND_CRON, KIND_REALTIME_CHANNEL),
        # Data
        (KIND_ENTITY, KIND_CACHE),
        # GraphQL schema + observability health checks for an entity
        (KIND_ENTITY, KIND_GRAPHQL),
        (KIND_ENTITY, KIND_HEALTH),
        (KIND_ENTITY, KIND_SEARCH_INDEX),
        (KIND_ENTITY, KIND_AUDIT_LOG),
        # Integrations
        (KIND_ROUTE, KIND_WEBHOOK),
        (KIND_ROUTE, KIND_FILE_UPLOAD),
        (KIND_FILE_UPLOAD, KIND_STORAGE_DRIVER),
        (KIND_ROUTE, KIND_REALTIME_CHANNEL),
        (KIND_ENTITY, KIND_EMAIL_TEMPLATE),
        # Feature flags (a route's policies/features socket targets the flag)
        (KIND_ROUTE, KIND_FEATURE_FLAG),
        # Contracts (routes declare their payload schema; optional entity
        # link documents which entity's data the contract shapes)
        (KIND_ROUTE, KIND_CONTRACT),
        (KIND_CONTRACT, KIND_ENTITY),
        # UI
        (KIND_PAGE, KIND_COMPONENT),
        (KIND_PAGE, KIND_ROUTE),
        (KIND_DASHBOARD, KIND_ENTITY),
    }
)

# ── Port constraints: compatible port types for connections ───────────

PORT_COMPATIBILITY: dict[str, frozenset[str]] = {
    PORT_TYPE_ENTITY_REF: frozenset({PORT_TYPE_ENTITY_REF}),
    PORT_TYPE_ROUTE_REF: frozenset({PORT_TYPE_ROUTE_REF}),
    PORT_TYPE_EVENT_REF: frozenset({PORT_TYPE_EVENT_REF}),
    PORT_TYPE_CONFIG_REF: frozenset({PORT_TYPE_CONFIG_REF}),
    PORT_TYPE_DATA_REF: frozenset({PORT_TYPE_DATA_REF}),
}

# ── Edge kind mapping: (source_kind, target_kind) -> edge_kind ───────

EDGE_KIND_MAP: dict[tuple[str, str], str] = {
    (KIND_ROUTE, KIND_ENTITY): "route_to_entity",
    (KIND_ENTITY, KIND_ENTITY): "entity_to_entity",
    (KIND_ENTITY, KIND_SERVICE): "entity_to_service",
    (KIND_ENTITY, KIND_SEEDER): "entity_to_seeder",
    (KIND_ENTITY, KIND_ERROR): "entity_to_error",
    (KIND_ENTITY, KIND_VALIDATOR): "entity_to_validator",
    (KIND_ROUTE, KIND_AUTH): "route_to_auth",
    (KIND_ROUTE, KIND_ROLE): "route_to_role",
    (KIND_ROLE, KIND_AUTH): "route_to_auth",
    (KIND_ENTITY, KIND_MIDDLEWARE): "entity_to_middleware",
    (KIND_ROUTE, KIND_MIDDLEWARE): "route_to_middleware",
    (KIND_ROUTE, KIND_RATE_LIMIT): "route_to_rate_limit",
    (KIND_ROUTE, KIND_EXCEPTION_FILTER): "route_to_exception_filter",
    (KIND_EXCEPTION_FILTER, KIND_EXCEPTION_FILTER): "filter_chain",
    (KIND_ENTITY, KIND_EVENT): "entity_to_event",
    (KIND_ENTITY, KIND_COMMAND): "entity_to_command",
    (KIND_ENTITY, KIND_QUERY): "entity_to_query",
    (KIND_EVENT, KIND_EVENT_HANDLER): "event_to_handler",
    (KIND_EVENT, KIND_PROJECTION): "event_to_projection",
    (KIND_EVENT, KIND_SAGA): "event_to_saga",
    (KIND_EVENT, KIND_JOB): "event_to_job",
    (KIND_CRON, KIND_JOB): "cron_to_job",
    (KIND_CRON, KIND_EVENT): "cron_to_event",
    (KIND_WEBHOOK, KIND_JOB): "webhook_to_job",
    (KIND_WEBHOOK, KIND_EVENT): "webhook_to_event",
    (KIND_WEBHOOK, KIND_REALTIME_CHANNEL): "webhook_to_channel",
    (KIND_EVENT, KIND_REALTIME_CHANNEL): "event_to_channel",
    (KIND_JOB, KIND_REALTIME_CHANNEL): "job_to_channel",
    (KIND_CRON, KIND_REALTIME_CHANNEL): "cron_to_channel",
    (KIND_ENTITY, KIND_CACHE): "entity_to_cache",
    (KIND_ENTITY, KIND_GRAPHQL): "entity_to_graphql",
    (KIND_ENTITY, KIND_HEALTH): "entity_to_health",
    (KIND_ENTITY, KIND_SEARCH_INDEX): "entity_to_search",
    (KIND_ENTITY, KIND_AUDIT_LOG): "entity_to_audit",
    (KIND_ROUTE, KIND_WEBHOOK): "route_to_webhook",
    (KIND_ROUTE, KIND_FILE_UPLOAD): "route_to_file_upload",
    (KIND_FILE_UPLOAD, KIND_STORAGE_DRIVER): "file_upload_to_storage_driver",
    (KIND_ROUTE, KIND_REALTIME_CHANNEL): "route_to_realtime",
    (KIND_ENTITY, KIND_EMAIL_TEMPLATE): "entity_to_email",
    (KIND_ROUTE, KIND_FEATURE_FLAG): "route_to_feature_flag",
    (KIND_ROUTE, KIND_CONTRACT): "route_to_contract",
    (KIND_CONTRACT, KIND_ENTITY): "contract_to_entity",
    (KIND_PAGE, KIND_COMPONENT): "page_to_component",
    (KIND_PAGE, KIND_ROUTE): "page_to_route",
    (KIND_DASHBOARD, KIND_ENTITY): "dashboard_to_entity",
}

# ── Node default configs ──────────────────────────────────────────────

NODE_DEFAULTS: dict[str, dict[str, object]] = {
    KIND_APP_SETTINGS: {
        "app_name": "my_app", "port": 8000, "db": "sqlite",
        "structure": "minimal", "description": "", "version": "0.1.0",
        "python_version": "3.13",
        "features": {
            "enableAuth": False, "enableAdmin": False, "enableApiDocs": True,
            "enableWebsockets": False, "enableBackgroundJobs": False,
            "enableSearch": False, "enableFileUpload": False,
            "enableAuditLog": False, "enableRateLimiting": False,
            "enableCaching": False, "enableEmail": False, "enableSse": False,
        },
    },
    KIND_ENTITY: {
        "name": "item", "plural": "items", "description": "",
        "tableName": "items", "timestamps": True, "softDelete": False,
        "Implements": [], "indexes": [], "tags": [],
    },
    KIND_FIELD: {
        "name": "title", "type": "str", "nullable": False,
        "default": None, "description": "",
        "constraints": {
            "minLength": None, "maxLength": None, "min": None, "max": None,
            "pattern": None, "unique": False, "indexed": False,
            "readOnly": False, "immutable": False,
        },
        "ui": {
            "label": "", "placeholder": "", "helpText": "",
            "hidden": False, "readOnly": False, "format": None, "options": None,
        },
    },
    KIND_ROUTE: {
        "pathPrefix": None, "ops": ["create", "get", "list", "update", "delete"],
        "auth": False, "rateLimit": None, "middleware": [],
        "description": "", "tags": [], "deprecated": False, "version": None,
    },
    KIND_AUTH: {
        "name": "jwt_auth", "provider": "jwt",
        "config": {
            "secret": None, "algorithm": "HS256", "oauthProviders": [],
            "apiKeyHeader": "X-API-Key", "apiKeyPrefix": None,
            "sessionBackend": "memory", "sessionTtl": 86400,
        },
        "userEntity": None, "loginPath": "/auth/login",
        "logoutPath": "/auth/logout", "registerPath": "/auth/register",
        "refreshToken": True, "tokenExpiry": "30m", "description": "",
    },
    KIND_ROLE: {
        "name": "user", "description": "", "permissions": [],
        "inherits": [], "isDefault": True, "color": "#6366f1",
    },
    KIND_MIDDLEWARE: {
        "name": "logging", "type": "logging", "config": {},
        "order": 100, "description": "", "appliesTo": ["all"],
    },
    KIND_VALIDATOR: {
        "name": "validate_item", "target": "entity",
        "rules": [], "description": "",
    },
    KIND_JOB: {
        "name": "process_data", "description": "", "queue": "default",
        "priority": "normal", "retries": 3, "timeout": "5m",
        "retryDelay": "30s", "concurrency": 1, "enabled": True, "triggers": [],
    },
    KIND_EVENT: {
        "name": "item.created", "description": "", "payload": [],
        "producers": [], "consumers": [], "async": True, "schema": {},
    },
    KIND_CACHE: {
        "name": "product_cache", "backend": "memory", "ttl": "5m",
        "maxSize": None, "keyPattern": "product:{id}",
        "invalidateOn": [], "enabled": True, "description": "",
    },
    KIND_GRAPHQL: {
        "name": "", "enabled": True, "description": "",
    },
    KIND_HEALTH: {
        "name": "", "critical": True, "enabled": True, "description": "",
    },
    KIND_EVENT_HANDLER: {
        "name": "", "event": "", "enabled": True, "description": "",
    },
    KIND_COMMAND: {
        "name": "", "side": "command", "entity": "", "fields": (),
        "enabled": True, "description": "",
    },
    KIND_QUERY: {
        "name": "", "side": "query", "entity": "", "fields": (),
        "enabled": True, "description": "",
    },
    KIND_PROJECTION: {
        "name": "", "events": (), "enabled": True, "description": "",
    },
    KIND_METRIC: {
        "name": "", "unit": "count", "enabled": True, "description": "",
    },
    KIND_SAGA: {
        "name": "", "enabled": True, "description": "",
    },
    KIND_API_CLIENT: {
        "name": "client", "baseUrl": "https://api.example.com",
        "authType": "apikey", "enabled": True, "description": "",
    },
    KIND_STORAGE_DRIVER: {
        "name": "driver", "driverType": "custom",
        "enabled": True, "description": "",
    },
    KIND_SEARCH_INDEX: {
        "name": "product_search", "entity": "", "fields": [],
        "engine": "fts", "boost": {}, "fuzzy": False,
        "suggestions": False, "description": "",
    },
    KIND_WEBHOOK: {
        "name": "notify_slack", "url": "", "method": "POST",
        "headers": {}, "auth": None, "events": [], "retries": 3,
        "timeout": "30s", "description": "", "enabled": True,
    },
    KIND_REALTIME_CHANNEL: {
        "name": "notifications", "channel": "notifications",
        "auth": True, "events": [], "presence": False,
        "history": False, "maxHistory": 100, "description": "",
    },
    KIND_FILE_UPLOAD: {
        "name": "avatar_upload", "storage": "local", "maxSize": "10MB",
        "allowedTypes": ["image/jpeg", "image/png"],
        "directory": "uploads/{entity}", "generateThumbnails": False,
        "thumbnailSizes": [], "description": "",
    },
    KIND_EMAIL_TEMPLATE: {
        "name": "welcome_email", "subject": "Welcome {{name}}!",
        "from": "noreply@app.com", "replyTo": None,
        "htmlTemplate": "", "textTemplate": None, "variables": [],
        "triggers": [], "enabled": True, "description": "",
    },
    KIND_PAGE: {
        "name": "home", "path": "/", "auth": False, "layout": None,
        "title": "Home", "description": "",
        "meta": {"breadcrumb": False, "backLink": None, "maxWidth": "1200px", "padding": "2rem"},
        "seo": {"title": None, "description": None, "ogImage": None, "noIndex": False},
    },
    KIND_COMPONENT: {
        "name": "data_table", "type": "data_table", "config": {},
        "description": "", "reusable": True,
    },
    KIND_DASHBOARD: {
        "name": "admin_dashboard", "path": "/admin", "layout": "grid",
        "widgets": [], "auth": True, "roles": ["admin"],
        "refreshInterval": None, "description": "",
    },
    KIND_API_KEY_GROUP: {
        "name": "partner_api", "description": "", "keyPrefix": "pk_",
        "keyHeader": "X-API-Key", "rateLimit": None, "permissions": [],
        "expiresAt": None, "enabled": True,
    },
    KIND_AUDIT_LOG: {
        "name": "audit", "entity": "", "operations": ["create", "update", "delete"],
        "captureFields": None, "captureRequestMeta": True,
        "retentionDays": 90, "excludeFields": ["password", "token"],
        "description": "",
    },
    KIND_RATE_LIMIT: {
        "name": "api_standard", "strategy": "fixed_window",
        "window": "1m", "maxRequests": 60, "keyBy": "ip",
        "response": {"statusCode": 429, "message": "Too many requests", "retryAfter": True, "headers": True},
        "description": "",
    },
    KIND_CRON: {
        "name": "daily_cleanup", "schedule": "0 2 * * *",
        "timezone": "UTC", "enabled": True, "description": "", "targets": [],
    },
    KIND_SERVICE: {
        "name": "", "enabled": True, "description": "",
    },
    KIND_SEEDER: {
        "name": "", "enabled": True, "description": "",
    },
    KIND_EXCEPTION_FILTER: {
        "name": "not_found", "exception_type": "ValueError",
        "status_code": 400, "enabled": True, "description": "",
    },
    KIND_ERROR: {
        "name": "", "status_code": 400, "error_code": "",
        "enabled": True, "description": "",
    },
    KIND_FEATURE_FLAG: {
        "name": "new_checkout", "enabled": True, "description": "",
    },
    KIND_CONTRACT: {
        "name": "create_order", "direction": "both", "fields": (),
        "entity": "", "enabled": True, "description": "",
    },
}

# ── Node kind colors (hex) ───────────────────────────────────────────

NODE_COLORS: dict[str, str] = {
    KIND_APP_SETTINGS: "#7c3aed",
    KIND_ENTITY: "#2563eb",
    KIND_FIELD: "#6366f1",
    KIND_ROUTE: "#059669",
    KIND_AUTH: "#8b5cf6",
    KIND_ROLE: "#a855f7",
    KIND_MIDDLEWARE: "#f59e0b",
    KIND_VALIDATOR: "#eab308",
    KIND_JOB: "#d97706",
    KIND_EVENT: "#06b6d4",
    KIND_CACHE: "#10b981",
    KIND_GRAPHQL: "#e535ab",
    KIND_HEALTH: "#16a34a",
    KIND_EVENT_HANDLER: "#0d9488",
    KIND_SEARCH_INDEX: "#059669",
    KIND_WEBHOOK: "#0891b2",
    KIND_REALTIME_CHANNEL: "#0e7490",
    KIND_FILE_UPLOAD: "#047857",
    KIND_EMAIL_TEMPLATE: "#34d399",
    KIND_PAGE: "#ec4899",
    KIND_COMPONENT: "#f472b6",
    KIND_DASHBOARD: "#db2777",
    KIND_API_KEY_GROUP: "#be185d",
    KIND_AUDIT_LOG: "#15803d",
    KIND_RATE_LIMIT: "#16a34a",
    KIND_CRON: "#ca8a04",
    KIND_SERVICE: "#0d9488",
    KIND_SEEDER: "#65a30d",
    KIND_EXCEPTION_FILTER: "#e11d48",
    KIND_ERROR: "#dc2626",
    KIND_COMMAND: "#ea580c",
    KIND_QUERY: "#0284c7",
    KIND_PROJECTION: "#4f46e5",
    KIND_METRIC: "#b45309",
    KIND_SAGA: "#7c3aed",
    KIND_API_CLIENT: "#0284c7",
    KIND_STORAGE_DRIVER: "#0f766e",
    KIND_FEATURE_FLAG: "#f43f5e",
    KIND_CONTRACT: "#0d9488",
}

# ── Palette categories for sidebar ────────────────────────────────────
#
# This is the DRAWABLE palette — only kinds that participate in the build
# graph and drive framework code generation. Inert/config kinds (app_settings,
# auth, role, rate_limit, api_key_group, email_template,
# page/component/dashboard) remain in KNOWN_KINDS
# (so existing saved graphs still validate/load) but are intentionally NOT
# draggable: they belong in dedicated screens/settings, not the graph.
# See docs/NODE_VS_SCREEN.md. audit_log graduated from the inert nine into an
# entity-attached generator (nodes plan N4.1); api_key_group became
# screen-driven — still Security-modal-only, but its config now persists and
# emits real lexigram-auth plumbing (nodes plan N4.2); email_template became
# screen-driven — still Emails-modal-only, emitting Mailable modules per
# enabled template (nodes plan N4.3). page/component/dashboard are RETIRED
# to an explicit frontend handoff (nodes plan N4.4): they stay in
# KNOWN_KINDS so legacy graphs load, but have no builder-side model or
# emission — the API builder's scope ends at the backend. Removal
# candidates for a future major version.

PALETTE_CATEGORIES: list[dict[str, object]] = [
    {
        "id": "core", "label": "Core", "icon": "layers", "color": "#3b82f6",
        "nodes": [
            {"kind": KIND_ENTITY, "label": "Entity", "description": "Database model with fields", "icon": "database", "color": NODE_COLORS[KIND_ENTITY], "maxCount": None, "required": False},
            {"kind": KIND_ROUTE, "label": "Route", "description": "API endpoint group (CRUD)", "icon": "globe", "color": NODE_COLORS[KIND_ROUTE], "maxCount": None, "required": False},
            {"kind": KIND_SERVICE, "label": "Service", "description": "Business-logic service for an entity", "icon": "workflow", "color": NODE_COLORS[KIND_SERVICE], "maxCount": None, "required": False},
            {"kind": KIND_GRAPHQL, "label": "GraphQL", "description": "Strawberry GraphQL schema for an entity", "icon": "share-2", "color": NODE_COLORS[KIND_GRAPHQL], "maxCount": None, "required": False},
        ],
    },
    {
        "id": "processing", "label": "Processing", "icon": "cpu", "color": "#f59e0b",
        "nodes": [
            {"kind": KIND_MIDDLEWARE, "label": "Middleware", "description": "Request/response pipeline", "icon": "filter", "color": NODE_COLORS[KIND_MIDDLEWARE], "maxCount": None, "required": False},
            {"kind": KIND_JOB, "label": "Background Job", "description": "Async task processor", "icon": "clock", "color": NODE_COLORS[KIND_JOB], "maxCount": None, "required": False},
            {"kind": KIND_CRON, "label": "Cron", "description": "Scheduled trigger", "icon": "calendar", "color": NODE_COLORS[KIND_CRON], "maxCount": None, "required": False},
            {"kind": KIND_EXCEPTION_FILTER, "label": "Exception Filter", "description": "Map exceptions to HTTP responses", "icon": "shield-alert", "color": NODE_COLORS[KIND_EXCEPTION_FILTER], "maxCount": None, "required": False},
            {"kind": KIND_ERROR, "label": "HTTP Error", "description": "Domain HTTP error class raised by handlers", "icon": "alert-octagon", "color": NODE_COLORS[KIND_ERROR], "maxCount": None, "required": False},
            {"kind": KIND_HEALTH, "label": "Health Check", "description": "Observability health probe for an entity", "icon": "heart-pulse", "color": NODE_COLORS[KIND_HEALTH], "maxCount": None, "required": False},
            {"kind": KIND_METRIC, "label": "Metric", "description": "Custom application metric recorded by services", "icon": "gauge", "color": NODE_COLORS[KIND_METRIC], "maxCount": None, "required": False},
            {"kind": KIND_API_CLIENT, "label": "API Client", "description": "Outbound HTTP client wrapping lexigram-http BaseURLHTTPClient", "icon": "globe", "color": NODE_COLORS[KIND_API_CLIENT], "maxCount": None, "required": False},
        ],
    },
    {
        "id": "events", "label": "Events & Messaging", "icon": "zap", "color": "#06b6d4",
        "nodes": [
            {"kind": KIND_EVENT, "label": "Domain Event", "description": "Async event emitter", "icon": "radio", "color": NODE_COLORS[KIND_EVENT], "maxCount": None, "required": False},
            {"kind": KIND_EVENT_HANDLER, "label": "Event Handler", "description": "In-process subscriber reacting to an event", "icon": "inbox", "color": NODE_COLORS[KIND_EVENT_HANDLER], "maxCount": None, "required": False},
            {"kind": KIND_COMMAND, "label": "Command", "description": "CQRS write intent with a handler on the command bus", "icon": "terminal", "color": NODE_COLORS[KIND_COMMAND], "maxCount": None, "required": False},
            {"kind": KIND_QUERY, "label": "Query", "description": "CQRS read request with a handler on the query bus", "icon": "search", "color": NODE_COLORS[KIND_QUERY], "maxCount": None, "required": False},
            {"kind": KIND_PROJECTION, "label": "Projection", "description": "Read-model view maintained by domain events", "icon": "table", "color": NODE_COLORS[KIND_PROJECTION], "maxCount": None, "required": False},
            {"kind": KIND_WEBHOOK, "label": "Webhook", "description": "Outbound HTTP call", "icon": "webhook", "color": NODE_COLORS[KIND_WEBHOOK], "maxCount": None, "required": False},
            {"kind": KIND_REALTIME_CHANNEL, "label": "Realtime Channel", "description": "WebSocket/SSE channel", "icon": "wifi", "color": NODE_COLORS[KIND_REALTIME_CHANNEL], "maxCount": None, "required": False},
        ],
    },
    {
        "id": "data", "label": "Data & Storage", "icon": "hard-drive", "color": "#10b981",
        "nodes": [
            {"kind": KIND_CACHE, "label": "Cache", "description": "Query result caching", "icon": "zap", "color": NODE_COLORS[KIND_CACHE], "maxCount": None, "required": False},
            {"kind": KIND_SEEDER, "label": "Seeder", "description": "Idempotent seed data for an entity", "icon": "sprout", "color": NODE_COLORS[KIND_SEEDER], "maxCount": None, "required": False},
            {"kind": KIND_AUDIT_LOG, "label": "Audit Log", "description": "Change trail for a wired entity - audit table migration, repository and create/update/delete hooks in its controller", "icon": "scroll-text", "color": NODE_COLORS[KIND_AUDIT_LOG], "maxCount": None, "required": False},
            {"kind": KIND_STORAGE_DRIVER, "label": "Storage Driver", "description": "Blob storage backend implementing lexigram-storage AbstractDriver", "icon": "hard-drive", "color": NODE_COLORS[KIND_STORAGE_DRIVER], "maxCount": None, "required": False},
        ],
    },
    {
        "id": "security", "label": "Security & Policy", "icon": "shield", "color": "#a855f7",
        "nodes": [
            {"kind": KIND_AUTH, "label": "Auth Provider", "description": "JWT / session / OAuth2 auth — guards wired routes with require_auth", "icon": "key", "color": NODE_COLORS[KIND_AUTH], "maxCount": None, "required": False},
            {"kind": KIND_ROLE, "label": "Role", "description": "Role with permissions — guards wired routes with require_roles", "icon": "users", "color": NODE_COLORS[KIND_ROLE], "maxCount": None, "required": False},
            {"kind": KIND_RATE_LIMIT, "label": "Rate Limit", "description": "API throttling policy; emits constants + enforcement middleware so wired routes 429 when exhausted", "icon": "shield-off", "color": NODE_COLORS[KIND_RATE_LIMIT], "maxCount": None, "required": False},
        ],
    },
    {
        "id": "platform", "label": "Platform", "icon": "flag", "color": "#f43f5e",
        "nodes": [
            {"kind": KIND_FEATURE_FLAG, "label": "Feature Flag", "description": "Feature flag definition wired from a route's Policies socket", "icon": "flag", "color": NODE_COLORS[KIND_FEATURE_FLAG], "maxCount": None, "required": False},
            {"kind": KIND_CONTRACT, "label": "Contract", "description": "Request/response payload schema swapped into wired routes' controllers", "icon": "file-json", "color": NODE_COLORS[KIND_CONTRACT], "maxCount": None, "required": False},
            {"kind": KIND_VALIDATOR, "label": "Validator", "description": "Reusable field constraints for a wired entity - emits src/app/validators/<entity>.py", "icon": "check-circle", "color": NODE_COLORS[KIND_VALIDATOR], "maxCount": None, "required": False},
            {"kind": KIND_SEARCH_INDEX, "label": "Search Index", "description": "SQLite FTS5 search over a wired entity - migration, repository and GET <route>/search", "icon": "scan-search", "color": NODE_COLORS[KIND_SEARCH_INDEX], "maxCount": None, "required": False},
            {"kind": KIND_FILE_UPLOAD, "label": "File Upload", "description": "Multipart upload endpoint for a wired route - local-disk storage with size/type validation", "icon": "upload", "color": NODE_COLORS[KIND_FILE_UPLOAD], "maxCount": None, "required": False},
        ],
    },
]

# ── Constraints ───────────────────────────────────────────────────────

PORT_MIN = 1024
PORT_MAX = 65535


def is_known_kind(kind: str) -> bool:
    """Return True when *kind* is in the palette."""
    return kind in KNOWN_KINDS


def is_snake_case_identifier(name: str) -> bool:
    """Return True for lowercase snake_case Python identifiers."""
    if not name or not name.isidentifier() or keyword.iskeyword(name):
        return False
    if not name[0].isalpha():
        return False
    return name == name.lower()


def is_valid_port(port: int) -> bool:
    """Return True when *port* fits the allowed bind range."""
    return PORT_MIN <= port <= PORT_MAX


def get_node_ports(kind: str) -> dict[str, list[dict[str, object]]]:
    """Return port definitions for a node kind."""
    return NODE_PORTS.get(kind, {"inputs": [], "outputs": []})


def get_edge_kind(source_kind: str, target_kind: str) -> str | None:
    """Return the edge kind for a valid source-target pair, or None."""
    return EDGE_KIND_MAP.get((source_kind, target_kind))


def can_connect(source_kind: str, target_kind: str) -> bool:
    """Return True if an edge is allowed between these node kinds."""
    return (source_kind, target_kind) in ALLOWED_EDGES
