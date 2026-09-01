"""Graph validation producing node-scoped diagnostics."""

from __future__ import annotations

import re

from lexigram.builder.exceptions import GraphValidationError
from lexigram.builder.graph.models import (
    ApiClientConfig,
    ApiKeyGroupConfig,
    AppSettingsConfig,
    AuditLogConfig,
    AuthConfig,
    ChannelConfig,
    ContractConfig,
    CronConfig,
    EmailTemplateConfig,
    EntityConfig,
    FeatureFlagConfig,
    FileUploadConfig,
    GraphDocument,
    GraphNode,
    JobConfig,
    MiddlewareConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
    SearchIndexConfig,
    StorageDriverConfig,
    ValidatedGraph,
    ValidatorConfig,
    WebhookConfig,
)
from lexigram.builder.graph.palette import (
    ALLOWED_EDGES,
    AUTH_PROVIDERS,
    DB_PRESETS,
    ENTITY_OPS,
    FIELD_TYPES,
    MIDDLEWARE_TYPES,
    PROJECT_STRUCTURES,
    RATE_LIMIT_STRATEGIES,
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
    if isinstance(node.config, MiddlewareConfig):
        return _check_middleware(node)
    if isinstance(node.config, CronConfig):
        return _check_cron(node)
    if isinstance(node.config, WebhookConfig):
        return _check_webhook(node)
    if isinstance(node.config, JobConfig):
        return _check_job(node)
    if isinstance(node.config, ChannelConfig):
        return _check_channel(node)
    if isinstance(node.config, FeatureFlagConfig):
        return _check_feature_flag(node)
    if isinstance(node.config, AuthConfig):
        return _check_auth(node)
    if isinstance(node.config, RoleConfig):
        return _check_role(node)
    if isinstance(node.config, RateLimitConfig):
        return _check_rate_limit(node)
    if isinstance(node.config, ContractConfig):
        return _check_contract(node)
    if isinstance(node.config, ValidatorConfig):
        return _check_validator(node)
    if isinstance(node.config, SearchIndexConfig):
        return _check_search_index(node)
    if isinstance(node.config, FileUploadConfig):
        return _check_file_upload(node)
    if isinstance(node.config, AuditLogConfig):
        return _check_audit_log(node)
    if isinstance(node.config, ApiKeyGroupConfig):
        return _check_api_key_group(node)
    if isinstance(node.config, EmailTemplateConfig):
        return _check_email_template(node)
    if node.kind == "saga":
        return _check_saga(node)
    if node.kind == "interceptor":
        return _check_interceptor(node)
    if node.kind == "dataloader":
        return _check_dataloader(node)
    if node.kind == "auth_policy":
        return _check_auth_policy(node)
    if node.kind == "api_client":
        return _check_api_client(node)
    if node.kind == "storage_driver":
        return _check_storage_driver(node)
    return []


def _check_job(node: GraphNode) -> list[Diagnostic]:
    config: JobConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(_diag(node, "invalid-job-name", "job task name must be snake_case"))
    return out


def _check_feature_flag(node: GraphNode) -> list[Diagnostic]:
    config: FeatureFlagConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(node, "invalid-flag-name", "flag name must be snake_case")
        )
    return out


def _check_auth(node: GraphNode) -> list[Diagnostic]:
    config: AuthConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(_diag(node, "invalid-auth-name", "auth name must be snake_case"))
    if config.provider not in AUTH_PROVIDERS:
        out.append(
            _diag(
                node,
                "unknown-auth-provider",
                f"provider {config.provider!r} not in {sorted(AUTH_PROVIDERS)}",
            )
        )
    return out


def _check_role(node: GraphNode) -> list[Diagnostic]:
    config: RoleConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(_diag(node, "invalid-role-name", "role name must be snake_case"))
    return out


def _check_rate_limit(node: GraphNode) -> list[Diagnostic]:
    config: RateLimitConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(node, "invalid-rate-limit-name", "rate limit name must be snake_case")
        )
    if config.strategy not in RATE_LIMIT_STRATEGIES:
        out.append(
            _diag(
                node,
                "unknown-rate-limit-strategy",
                f"strategy {config.strategy!r} not in {sorted(RATE_LIMIT_STRATEGIES)}",
            )
        )
    if config.max_requests < 1:
        out.append(
            _diag(node, "invalid-rate-limit-max", "max_requests must be at least 1")
        )
    return out


def _check_contract(node: GraphNode) -> list[Diagnostic]:
    config: ContractConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(node, "invalid-contract-name", "contract name must be snake_case")
        )
    if config.direction not in ("request", "response", "both"):
        out.append(
            _diag(
                node,
                "invalid-contract-direction",
                f"direction {config.direction!r} must be request, response or both",
            )
        )
    if config.enabled and not config.fields and not config.entity:
        out.append(
            _diag(
                node,
                "contract-requires-fields",
                "an enabled contract needs fields or an entity reference "
                "so its models have a shape",
            )
        )
    for field_name, field_type in config.fields:
        if not field_name:
            out.append(
                _diag(node, "invalid-contract-field", "field names must be non-empty")
            )
            break
        if field_type not in FIELD_TYPES:
            out.append(
                _diag(
                    node,
                    "unknown-contract-field-type",
                    f"field {field_name!r} has type {field_type!r} "
                    f"not in {sorted(FIELD_TYPES)}",
                )
            )
    return out


_VALIDATOR_KWARGS = {
    "ge", "le", "gt", "lt", "min_length", "max_length", "pattern",
    "multiple_of",
}
_VALIDATOR_NUMERIC = {
    "ge", "le", "gt", "lt", "min_length", "max_length", "multiple_of",
}


def parse_constraint_expr(expr: str) -> dict[str, int | float | str]:
    """Parse ``"ge=0,le=1000"`` into a kwargs dict; raises ``ValueError``."""
    out: dict[str, int | float | str] = {}
    for token in expr.split(","):
        token = token.strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"constraint {token!r} must look like kwarg=value")
        key, _, raw = token.partition("=")
        key = key.strip()
        if key not in _VALIDATOR_KWARGS:
            raise ValueError(
                f"unknown constraint {key!r} (supported: {sorted(_VALIDATOR_KWARGS)})"
            )
        raw = raw.strip()
        if key == "pattern":
            try:
                re.compile(raw)
            except re.error as exc:
                raise ValueError(f"invalid pattern {raw!r}: {exc}") from exc
            out[key] = raw
            continue
        if key in _VALIDATOR_NUMERIC:
            try:
                value: int | float = int(raw)
            except ValueError:
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise ValueError(
                        f"constraint {key!r} needs a number, got {raw!r}"
                    ) from exc
            out[key] = value
            continue
        out[key] = raw
    return out


def _check_validator(node: GraphNode) -> list[Diagnostic]:
    config: ValidatorConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(node, "invalid-validator-name", "validator name must be snake_case")
        )
    if config.enabled and not config.rules:
        out.append(
            _diag(
                node,
                "validator-requires-rules",
                "an enabled validator needs at least one field rule",
            )
        )
    seen: set[str] = set()
    for field, expr in config.rules:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", field):
            out.append(
                _diag(
                    node,
                    "invalid-validator-field",
                    f"field {field!r} must be a snake_case identifier",
                )
            )
        if field in seen:
            out.append(
                _diag(
                    node,
                    "duplicate-validator-field",
                    f"field {field!r} appears more than once",
                )
            )
        seen.add(field)
        try:
            parse_constraint_expr(expr)
        except ValueError as exc:
            out.append(_diag(node, "invalid-validator-constraint", str(exc)))
    return out


_SEARCH_ENGINES = ("like", "fts", "meilisearch", "elasticsearch")


def _check_search_index(node: GraphNode) -> list[Diagnostic]:
    config: SearchIndexConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(
                node,
                "invalid-search-index-name",
                "search index name must be snake_case",
            )
        )
    if config.engine not in _SEARCH_ENGINES:
        out.append(
            _diag(
                node,
                "invalid-search-engine",
                f"engine {config.engine!r} must be one of "
                f"{sorted(_SEARCH_ENGINES)}",
            )
        )
    if config.enabled and not config.fields:
        out.append(
            _diag(
                node,
                "search-index-requires-fields",
                "an enabled search index needs at least one indexed field",
            )
        )
    for field in config.fields:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", field):
            out.append(
                _diag(
                    node,
                    "invalid-search-field",
                    f"indexed field {field!r} must be a snake_case identifier",
                )
            )
    for key, weight in (config.boost or {}).items():
        if key not in config.fields:
            out.append(
                _diag(
                    node,
                    "unknown-boost-field",
                    f"boost references {key!r} which is not an indexed field",
                )
            )
        elif weight < 0:
            out.append(
                _diag(
                    node,
                    "invalid-boost-weight",
                    f"boost weight for {key!r} must be >= 0",
                )
            )
    return out


_STORAGE_BACKENDS = ("local", "s3", "gcs", "azure_blob")
_MAX_SIZE_RE = re.compile(r"^\d+(\.\d+)?\s?(kb|mb|gb)$", re.IGNORECASE)
_FIT_MODES = ("cover", "contain", "fill")


def _check_file_upload(node: GraphNode) -> list[Diagnostic]:
    config: FileUploadConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(
                node,
                "invalid-file-upload-name",
                "file upload name must be snake_case",
            )
        )
    if config.storage not in _STORAGE_BACKENDS:
        out.append(
            _diag(
                node,
                "invalid-storage-backend",
                f"storage {config.storage!r} must be one of "
                f"{sorted(_STORAGE_BACKENDS)}",
            )
        )
    if not _MAX_SIZE_RE.match(config.max_size.strip()):
        out.append(
            _diag(
                node,
                "invalid-file-upload-max-size",
                f"max_size {config.max_size!r} must look like '5MB', "
                "'512KB' or '1GB'",
            )
        )
    if config.enabled and not config.allowed_types:
        out.append(
            _diag(
                node,
                "file-upload-requires-types",
                "an enabled file upload needs at least one allowed type "
                "(MIME like 'image/png', wildcard like 'image/*', or "
                "extension like '.pdf')",
            )
        )
    for allowed in config.allowed_types:
        kind_ok = (
            (":" in allowed or "/" in allowed or "*" in allowed)
            or allowed.startswith(".")
        )
        if not kind_ok or ("*" in allowed and not allowed.endswith("/*")):
            out.append(
                _diag(
                    node,
                    "invalid-file-upload-type",
                    f"allowed type {allowed!r} must be a MIME type "
                    "('image/png'), wildcard ('image/*') or extension "
                    "('.pdf')",
                )
            )
    directory = config.directory.strip()
    if (
        not directory
        or directory.startswith("/")
        or ".." in directory.split("/")
        or not re.fullmatch(r"[A-Za-z0-9_./-]+", directory)
    ):
        out.append(
            _diag(
                node,
                "invalid-file-upload-directory",
                f"directory {config.directory!r} must be a relative path "
                "without '..' segments",
            )
        )
    for size in config.thumbnail_sizes:
        if size.width <= 0 or size.height <= 0:
            out.append(
                _diag(
                    node,
                    "invalid-thumbnail-size",
                    f"thumbnail {size.width}x{size.height} must be positive",
                )
            )
        if size.fit not in _FIT_MODES:
            out.append(
                _diag(
                    node,
                    "invalid-thumbnail-fit",
                    f"thumbnail fit {size.fit!r} must be one of "
                    f"{sorted(_FIT_MODES)}",
                )
            )
    return out


def _check_channel(node: GraphNode) -> list[Diagnostic]:
    config: ChannelConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(node, "invalid-channel-name", "channel name must be snake_case")
        )
    if not _is_valid_path(config.path):
        out.append(
            _diag(
                node,
                "invalid-channel-path",
                f"path {config.path!r} must be an absolute path like /ws/chat",
            )
        )
    return out


def _check_webhook(node: GraphNode) -> list[Diagnostic]:
    config: WebhookConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(node, "invalid-webhook-name", "webhook name must be snake_case")
        )
    if not _is_valid_path(config.path):
        out.append(
            _diag(
                node,
                "invalid-webhook-path",
                f"path {config.path!r} must be an absolute path like /webhooks/x",
            )
        )
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", config.secret_env):
        out.append(
            _diag(
                node,
                "invalid-webhook-secret-env",
                f"secret_env {config.secret_env!r} must be UPPER_SNAKE_CASE",
            )
        )
    return out


def _is_valid_path(path: str) -> bool:
    """A relative-less absolute URL path of ``/snake/segments``."""
    import re

    return bool(
        path.startswith("/")
        and not path.endswith("/")
        and re.fullmatch(r"/[A-Za-z0-9_{}/-]+", path)
        and "//" not in path
    )


def _check_cron(node: GraphNode) -> list[Diagnostic]:
    config: CronConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(node, "invalid-cron-name", "cron task name must be snake_case")
        )
    if not _is_valid_cron(config.schedule):
        out.append(
            _diag(
                node,
                "invalid-cron-schedule",
                f"schedule {config.schedule!r} is not a 5-field cron expression",
            )
        )
    return out


def _check_middleware(node: GraphNode) -> list[Diagnostic]:
    config: MiddlewareConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(node, "invalid-middleware-name", "middleware name must be snake_case")
        )
    if config.type not in MIDDLEWARE_TYPES:
        out.append(
            _diag(
                node,
                "unknown-middleware-type",
                f"type {config.type!r} not in {sorted(MIDDLEWARE_TYPES)}",
            )
        )
    return out


def _diag(node: GraphNode, code: str, message: str) -> Diagnostic:
    return Diagnostic(
        node_id=node.id, severity=DiagnosticSeverity.ERROR, code=code, message=message
    )


def _is_valid_cron(schedule: str) -> bool:
    """Best-effort 5-field cron expression validation.

    Accepts ``*``, numbers, comma lists, ranges (``1-5``) and steps
    (``*/5``) for minute/hour/day-of-month/month/day-of-week, enforcing
    each field's numeric range.  Intentionally permissive beyond shape —
    the scheduler remains the final authority at boot.
    """
    import re

    fields = schedule.split()
    if len(fields) != 5:
        return False
    # (lo, hi) for minute, hour, day-of-month, month, day-of-week.
    ranges = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))
    token = re.compile(r"^(\*|\*/(\d+)|\d+(-\d+)?(,\d+(-\d+)?)*)$")
    for field, (lo, hi) in zip(fields, ranges, strict=True):
        match = token.match(field)
        if not match:
            return False
        # Validate every explicit number against the field range.
        for number in re.findall(r"\d+", field):
            # Skip the step denominator of `*/n` — only `n` is present there.
            if not lo <= int(number) <= hi:
                return False
    return True


def _check_app_settings(node: GraphNode) -> list[Diagnostic]:
    config: AppSettingsConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.app_name):
        out.append(_diag(node, "invalid-app-name", "app_name must be snake_case"))
    if not is_valid_port(config.port):
        out.append(
            _diag(node, "port-out-of-range", f"port {config.port} outside 1024-65535")
        )
    if config.structure not in PROJECT_STRUCTURES:
        out.append(
            _diag(
                node,
                "unknown-structure",
                f"structure must be one of {sorted(PROJECT_STRUCTURES)}",
            )
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
    if config.style not in ("controller", "resource"):
        out.append(
            _diag(node, "invalid-route-style", "route style must be controller or resource")
        )
    return out


__all__ = ["validate"]


_AUDITABLE_OPS = frozenset({"create", "update", "delete"})


def _check_audit_log(node: GraphNode) -> list[Diagnostic]:
    config: AuditLogConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(node, "invalid-audit-log-name", "audit log name must be snake_case")
        )
    if config.enabled and not config.operations:
        out.append(
            _diag(
                node,
                "audit-log-requires-operations",
                "an enabled audit log needs at least one audited operation",
            )
        )
    for op in config.operations:
        if op not in _AUDITABLE_OPS:
            out.append(
                _diag(
                    node,
                    "invalid-audit-operation",
                    f"operation {op!r} must be one of {sorted(_AUDITABLE_OPS)}"
                    " (reads are never audited)",
                )
            )
    seen: set[str] = set()
    for field in config.capture_fields:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", field):
            out.append(
                _diag(
                    node,
                    "invalid-audit-capture-field",
                    f"captured field {field!r} must be a snake_case identifier",
                )
            )
        if field in seen:
            out.append(
                _diag(
                    node,
                    "duplicate-audit-capture-field",
                    f"captured field {field!r} appears more than once",
                )
            )
        seen.add(field)
    for field in config.exclude_fields:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", field):
            out.append(
                _diag(
                    node,
                    "invalid-audit-exclude-field",
                    f"excluded field {field!r} must be a snake_case identifier",
                )
            )
        if field in seen:
            out.append(
                _diag(
                    node,
                    "duplicate-audit-exclude-field",
                    f"excluded field {field!r} appears more than once",
                )
            )
        seen.add(field)
    return out


_HEADER_TOKEN = re.compile(r"^[A-Za-z0-9-]+$")
_KEY_PREFIX = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _check_api_key_group(node: GraphNode) -> list[Diagnostic]:
    config: ApiKeyGroupConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(
                node,
                "invalid-api-key-group-name",
                "api key group name must be snake_case",
            )
        )
    if not _KEY_PREFIX.match(config.key_prefix):
        out.append(
            _diag(
                node,
                "invalid-api-key-prefix",
                "key prefix must start with a letter and contain only"
                " letters, digits and underscores",
            )
        )
    if not _HEADER_TOKEN.match(config.key_header):
        out.append(
            _diag(
                node,
                "invalid-api-key-header",
                "key header must be an HTTP header token (letters, digits,"
                " hyphens)",
            )
        )
    seen: set[str] = set()
    for perm in config.permissions:
        if not is_snake_case_identifier(perm.resource):
            out.append(
                _diag(
                    node,
                    "invalid-api-key-permission",
                    f"permission resource {perm.resource!r} must be a"
                    " snake_case identifier",
                )
            )
        if perm.resource in seen:
            out.append(
                _diag(
                    node,
                    "duplicate-api-key-permission",
                    f"permission for resource {perm.resource!r} appears more"
                    " than once",
                )
            )
        seen.add(perm.resource)
    return out


_EMAIL_PLACEHOLDER = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")


def _check_email_template(node: GraphNode) -> list[Diagnostic]:
    config: EmailTemplateConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(
                node,
                "invalid-email-template-name",
                "email template name must be snake_case",
            )
        )
    if config.enabled and not config.subject.strip():
        out.append(
            _diag(
                node,
                "email-template-requires-subject",
                "enabled templates need a subject line",
            )
        )
    if config.enabled and not config.html_template.strip():
        out.append(
            _diag(
                node,
                "email-template-requires-html",
                "enabled templates need an HTML body",
            )
        )
    names: set[str] = set()
    for var in config.variables:
        if not is_snake_case_identifier(var.name):
            out.append(
                _diag(
                    node,
                    "invalid-email-variable-name",
                    f"merge variable {var.name!r} must be a snake_case"
                    " identifier",
                )
            )
        if var.type not in FIELD_TYPES:
            out.append(
                _diag(
                    node,
                    "invalid-email-variable-type",
                    f"merge variable {var.name!r} has unknown type"
                    f" {var.type!r}",
                )
            )
        if var.name in names:
            out.append(
                _diag(
                    node,
                    "duplicate-email-variable",
                    f"merge variable {var.name!r} appears more than once",
                )
            )
        names.add(var.name)
    for field_label, template in (
        ("subject", config.subject),
        ("html", config.html_template),
        ("text", config.text_template),
    ):
        for ref in _EMAIL_PLACEHOLDER.findall(template):
            if ref not in names:
                out.append(
                    _diag(
                        node,
                        "unknown-email-variable",
                        f"{field_label} template references {ref!r} which is"
                        " not a declared merge variable",
                    )
                )
    return out


def _check_saga(node: GraphNode) -> list[Diagnostic]:
    config = node.config
    out: list[Diagnostic] = []
    name = getattr(config, "name", "")
    if not is_snake_case_identifier(str(name)):
        out.append(_diag(node, "invalid-saga-name", "saga name must be snake_case"))
    return out


def _check_interceptor(node: GraphNode) -> list[Diagnostic]:
    config = node.config
    out: list[Diagnostic] = []
    name = getattr(config, "name", "")
    if not is_snake_case_identifier(str(name)):
        out.append(
            _diag(node, "invalid-interceptor-name", "interceptor name must be snake_case")
        )
    return out


def _check_dataloader(node: GraphNode) -> list[Diagnostic]:
    config = node.config
    out: list[Diagnostic] = []
    name = getattr(config, "name", "")
    if not is_snake_case_identifier(str(name)):
        out.append(
            _diag(node, "invalid-dataloader-name", "dataloader name must be snake_case")
        )
    key_type = str(getattr(config, "key_type", "str"))
    if key_type not in ("str", "int", "uuid"):
        out.append(
            _diag(node, "invalid-dataloader-key-type", "dataloader key_type must be str, int, or uuid")
        )
    return out


def _check_auth_policy(node: GraphNode) -> list[Diagnostic]:
    config = node.config
    out: list[Diagnostic] = []
    name = getattr(config, "name", "")
    if not is_snake_case_identifier(str(name)):
        out.append(
            _diag(node, "invalid-auth-policy-name", "auth policy name must be snake_case")
        )
    return out



def _check_api_client(node: GraphNode) -> list[Diagnostic]:
    config = node.config
    out: list[Diagnostic] = []
    if not isinstance(config, ApiClientConfig):
        return out
    if not is_snake_case_identifier(config.name):
        out.append(_diag(node, "invalid-api-client-name", "api client name must be snake_case"))
    if config.auth_type not in ("none", "apikey", "bearer"):
        out.append(
            _diag(
                node,
                "invalid-api-client-auth",
                f"auth_type {config.auth_type!r} must be none, apikey or bearer",
            )
        )
    url = config.base_url.strip()
    if config.enabled and url and not url.startswith(("http://", "https://")):
        out.append(_diag(node, "invalid-api-client-url", "base_url must be an http(s) URL"))
    return out


def _check_storage_driver(node: GraphNode) -> list[Diagnostic]:
    config = node.config
    out: list[Diagnostic] = []
    if not isinstance(config, StorageDriverConfig):
        return out
    if not is_snake_case_identifier(config.name):
        out.append(
            _diag(node, "invalid-storage-driver-name", "storage driver name must be snake_case")
        )
    if config.driver_type not in ("custom", "s3", "gcs", "azure", "local"):
        out.append(
            _diag(
                node,
                "invalid-storage-driver-type",
                f"driver_type {config.driver_type!r} must be custom, s3, gcs, azure or local",
            )
        )
    return out
