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
    ModuleConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
    SearchIndexConfig,
    StorageDriverConfig,
    ValidatedGraph,
    ValidatorConfig,
    WebhookConfig,
)
from lexigram.builder.graph.modules import drop_muted, module_import_graph
from lexigram.builder.graph.palette import (
    ALLOWED_EDGES,
    AUTH_PROVIDERS,
    DB_PRESETS,
    ENTITY_OPS,
    FIELD_TYPES,
    KIND_MODULE,
    MIDDLEWARE_TYPES,
    MODULE_SCOPED_KINDS,
    RATE_LIMIT_STRATEGIES,
    SHARED_KINDS,
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

    **Muting is applied here, once.** A muted node is excluded from
    generation, so it is excluded from validation too: the alternative --
    validating what will not be built -- makes mute useless for its main
    purpose, which is parking something half-drawn while the rest of the
    app keeps generating. This is the single seam where the authored graph
    becomes the live one; the writer, the preview and the module map all
    read the result rather than each deciding for itself. The drawing is
    not lost: it rides along as ``ValidatedGraph.authored``.
    """
    authored = document
    document = drop_muted(document)
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
    #: Which module first claimed each entity name, so a cross-module clash
    #: can say why the boundary does not protect it.
    entity_modules: dict[str, str | None] = {}
    for node in document.nodes:
        diagnostics.extend(_check_node(node, entity_names, entity_modules))

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
    # A route can also be orphaned *by muting*: it is wired on the canvas,
    # to something that will not be generated. Saying "wire this to an
    # entity" there is a diagnostic about a graph the user cannot see, so
    # the muted cause is named instead. Muting does not cascade -- excluding
    # nodes the user did not exclude is a worse surprise than an error that
    # says exactly what to do.
    muted_targets: dict[str, list[str]] = {}
    muted_ids = {node.id for node in authored.nodes} - {
        node.id for node in document.nodes
    }
    for edge in authored.edges:
        if edge.dst in muted_ids and edge.src not in muted_ids:
            muted_targets.setdefault(edge.src, []).append(edge.dst)
    for node in document.nodes:
        if node.kind == "route" and node.id not in connected_route_ids:
            muted_deps = muted_targets.get(node.id)
            message = (
                "Route is wired to muted node(s) "
                f"{', '.join(sorted(muted_deps))}, which are excluded from "
                "generation -- mute this route too, or unmute them"
                if muted_deps
                else "Route nodes must be wired to an entity"
            )
            diagnostics.append(
                Diagnostic(
                    node_id=node.id,
                    severity=DiagnosticSeverity.ERROR,
                    code="orphan-route",
                    message=message,
                )
            )

    diagnostics.extend(_check_modules(document, by_id))

    errors = [d for d in diagnostics if d.severity is DiagnosticSeverity.ERROR]
    if errors:
        return Err(
            GraphValidationError(
                f"Graph validation failed with {len(errors)} error(s)",
                diagnostics=tuple(diagnostics),
            )
        )
    return Ok(
        ValidatedGraph(
            document=document,
            diagnostics=tuple(diagnostics),
            authored=authored,
        )
    )


def _check_node(
    node: GraphNode,
    entity_names: dict[str, str],
    entity_modules: dict[str, str | None] | None = None,
) -> list[Diagnostic]:
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
        return _check_entity(node, entity_names, entity_modules)
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


def _diag(
    node: GraphNode, code: str, message: str, hint: str | None = None
) -> Diagnostic:
    return Diagnostic(
        node_id=node.id,
        severity=DiagnosticSeverity.ERROR,
        code=code,
        message=message,
        hint=hint,
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
    if config.db not in DB_PRESETS:
        out.append(
            _diag(
                node,
                "invalid-db-preset",
                f"db must be one of {sorted(DB_PRESETS)}",
            )
        )
    out.extend(_check_profiles(node, config))
    return out


#: A profile name becomes part of a filename (``application.<p>.yaml``) and
#: the value of ``LEX_PROFILE``. Restricting it to this shape is what stops
#: a canvas field from being a path: ``../../etc/passwd`` or ``a/b`` would
#: otherwise decide where the writer puts a file.
_PROFILE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _check_profiles(node: GraphNode, config: AppSettingsConfig) -> list[Diagnostic]:
    """Reject profile names that cannot safely become a filename."""
    out: list[Diagnostic] = []
    for profile in config.profiles:
        if _PROFILE_RE.match(profile):
            continue
        out.append(
            _diag(
                node,
                "app.invalid-profile",
                f"profile {profile!r} must be lowercase letters, digits and "
                f"underscores, starting with a letter",
                hint=(
                    "The name is used verbatim as `application.<profile>.yaml` "
                    "and as the value of LEX_PROFILE."
                ),
            )
        )
    return out


def _check_entity(
    node: GraphNode,
    entity_names: dict[str, str],
    entity_modules: dict[str, str | None] | None = None,
) -> list[Diagnostic]:
    config: EntityConfig = node.config  # type: ignore[assignment]
    out: list[Diagnostic] = []
    if not is_snake_case_identifier(config.name):
        out.append(_diag(node, "invalid-entity-name", "name must be snake_case"))
    elif config.name in entity_names:
        # Worth spelling out when the two entities sit in different bounded
        # contexts: the module boundary makes it look safe, and it is not.
        # Modules are a Python-package boundary, not a database one -- one
        # schema, one alembic history, so two `invoice` entities compete for
        # one table however far apart they are drawn.
        other = entity_names[config.name]
        hint = None
        claimed_by = (entity_modules or {}).get(config.name)
        if node.module is not None and claimed_by not in (None, node.module):
            hint = (
                f"Modules {claimed_by!r} and "
                f"{node.module!r} would share one table: table names are "
                f"global. Rename one entity."
            )
        out.append(
            _diag(
                node,
                "duplicate-entity-name",
                f"Entity name {config.name!r} already used by {other}",
                hint=hint,
            )
        )
    else:
        entity_names[config.name] = node.id
        if entity_modules is not None:
            entity_modules[config.name] = node.module

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


#: Slugs a module may not use: each already names a directory the modular
#: layout generates, so a module of the same name would collide with it.
RESERVED_MODULE_SLUGS: frozenset[str] = frozenset(
    {"shared", "infrastructure", "modules", "app", "tests", "migrations", "seeds"}
)


def _import_cycles(imports: dict[str, set[str]]) -> list[tuple[str, ...]]:
    """Return one canonical representative per import cycle.

    Reported once per cycle rather than once per participating edge: a
    two-module cycle is one mistake, and two diagnostics describing the
    same loop from different ends read like two problems.

    Iterative depth-first search with an explicit stack -- a graph drawn by
    a user can be wide, and recursion depth is not a budget worth spending
    on a linter.
    """
    cycles: list[tuple[str, ...]] = []
    seen: set[frozenset[str]] = set()
    finished: set[str] = set()

    for root in sorted(imports):
        if root in finished:
            continue
        path: list[str] = []
        on_path: set[str] = set()
        stack: list[tuple[str, bool]] = [(root, False)]
        while stack:
            node, leaving = stack.pop()
            if leaving:
                on_path.discard(path.pop())
                finished.add(node)
                continue
            if node in on_path:
                loop = tuple(path[path.index(node):])
                key = frozenset(loop)
                if key not in seen:
                    seen.add(key)
                    cycles.append((*loop, node))
                continue
            if node in finished:
                continue
            path.append(node)
            on_path.add(node)
            stack.append((node, True))
            for nxt in sorted(imports.get(node, ()), reverse=True):
                stack.append((nxt, False))
    return cycles


def _check_modules(
    document: GraphDocument, by_id: dict[str, GraphNode]
) -> list[Diagnostic]:
    """Validate Module nodes and the module scope other nodes point at.

    A Module is a scope, not an emitter, so every rule here is about
    *references* holding together: slugs are well-formed and unique, every
    scope points at a real module, and cross-module dependencies stay
    inside the exported surface.

    Severities follow ``01-NODE_TAXONOMY.md`` §4. ``boundary_unexported`` is
    a warning while modules are visual-only; it becomes an error when
    modular codegen lands, because from then on the generated app would
    fail to boot and a canvas that lets you draw an unbootable app is worse
    than one that stops you.
    """
    diagnostics: list[Diagnostic] = []
    module_nodes = [n for n in document.nodes if n.kind == KIND_MODULE]

    slugs: dict[str, str] = {}
    for node in module_nodes:
        config = node.config
        if not isinstance(config, ModuleConfig):
            continue
        name = config.name

        if not is_snake_case_identifier(name):
            diagnostics.append(
                Diagnostic(
                    node_id=node.id,
                    severity=DiagnosticSeverity.ERROR,
                    code="module.name_invalid",
                    message=(
                        f"Module slug {name!r} is not snake_case; it becomes a "
                        f"Python package directory"
                    ),
                    hint="Use lowercase words joined by underscores, e.g. 'sales'.",
                )
            )
        elif name in RESERVED_MODULE_SLUGS:
            diagnostics.append(
                Diagnostic(
                    node_id=node.id,
                    severity=DiagnosticSeverity.ERROR,
                    code="module.reserved",
                    message=(
                        f"Module slug {name!r} is reserved by the modular layout"
                    ),
                    hint=(
                        "Pick a name that is not one of: "
                        f"{', '.join(sorted(RESERVED_MODULE_SLUGS))}."
                    ),
                )
            )

        if name in slugs:
            diagnostics.append(
                Diagnostic(
                    node_id=node.id,
                    severity=DiagnosticSeverity.ERROR,
                    code="module.duplicate",
                    message=f"Module slug {name!r} is already used by another module",
                    hint="Module slugs must be unique; they name a directory.",
                )
            )
        else:
            slugs[name] = node.id

        if node.module is not None:
            diagnostics.append(
                Diagnostic(
                    node_id=node.id,
                    severity=DiagnosticSeverity.ERROR,
                    code="module.nested",
                    message="A module cannot itself belong to a module",
                    hint=(
                        "Modules are peers. Draw a module-to-module edge to "
                        "express a dependency instead of nesting."
                    ),
                )
            )

    # ── every scope reference resolves ───────────────────────────────────
    for node in document.nodes:
        if node.module is not None and node.module not in slugs:
            diagnostics.append(
                Diagnostic(
                    node_id=node.id,
                    severity=DiagnosticSeverity.ERROR,
                    code="module.unknown_ref",
                    message=(
                        f"Node is scoped to module {node.module!r}, which does "
                        f"not exist"
                    ),
                    hint=(
                        "Add a module node with that slug, or clear the node's "
                        "module scope to make it shared."
                    ),
                )
            )

    # ── cross-module dependencies stay inside the exported surface ───────
    #
    # Severity is a policy the graph carries. With ``strict_boundaries`` on,
    # an unexported cross-module dependency is an error: the generated app
    # really does hide that name behind ``protocols.py``, so the canvas would
    # otherwise let you draw an import that cannot exist. Otherwise it stays
    # a warning -- a graph mid-draw should not be blocked from saving.
    settings_node = next(
        (n for n in document.nodes if n.kind == "app_settings"), None
    )
    settings_config = settings_node.config if settings_node is not None else None
    boundary_severity = (
        DiagnosticSeverity.ERROR
        if getattr(settings_config, "strict_boundaries", False)
        else DiagnosticSeverity.WARNING
    )

    exports_by_slug: dict[str, set[str]] = {}
    for node in module_nodes:
        if isinstance(node.config, ModuleConfig):
            exports_by_slug[node.config.name] = {
                export.implementation for export in node.config.exports
            } | {export.protocol for export in node.config.exports}

    for edge in document.edges:
        src = by_id.get(edge.src)
        dst = by_id.get(edge.dst)
        if src is None or dst is None or src.module == dst.module:
            continue

        if src.module is None and dst.module is not None:
            diagnostics.append(
                Diagnostic(
                    node_id=edge.src,
                    severity=DiagnosticSeverity.WARNING,
                    code="module.shared_depends_on_module",
                    message=(
                        f"Shared node depends on {dst.module!r}, inverting the "
                        f"dependency direction"
                    ),
                    hint=(
                        "Shared code should not know about a bounded context. "
                        "Move the node into the module, or depend on a "
                        "protocol the module exports."
                    ),
                )
            )
            continue

        if dst.module is None:
            continue  # depending on shared code is always allowed

        exported = exports_by_slug.get(dst.module, set())
        target_name = getattr(dst.config, "name", None)
        if dst.id not in exported and (
            target_name is None or target_name not in exported
        ):
            diagnostics.append(
                Diagnostic(
                    node_id=edge.src,
                    severity=boundary_severity,
                    code="module.boundary_unexported",
                    message=(
                        f"Module {src.module!r} depends on something "
                        f"{dst.module!r} does not export"
                    ),
                    hint=(
                        f"Add it to {dst.module!r}'s exports, mark that module "
                        f"is_global, or depend on a protocol it already "
                        f"exports."
                        + (
                            ""
                            if boundary_severity is DiagnosticSeverity.WARNING
                            else " (strict boundaries are on for this project.)"
                        )
                    ),
                )
            )

    # ── a shared component cannot live inside a bounded context ──────────
    for node in document.nodes:
        if node.module is not None and node.kind in SHARED_KINDS:
            diagnostics.append(
                Diagnostic(
                    node_id=node.id,
                    severity=DiagnosticSeverity.WARNING,
                    code="module.shared_kind_scoped",
                    message=(
                        f"{node.kind!r} is a cross-cutting component, so it is "
                        f"generated into shared/ regardless of the "
                        f"{node.module!r} scope"
                    ),
                    hint=(
                        "Clear the module scope to match where the file "
                        "actually lands, or keep it as canvas grouping only."
                    ),
                )
            )

    # A module-local kind with no module used to be an error here: under
    # the old ``modular`` structure there was nowhere to put unscoped
    # feature code, so the graph had to be rejected. There is now: it lands
    # at the app root, and joining a module moves it. The rule is not fixed,
    # it is unnecessary.

    # ── import edges between frames (taxonomy T6) ────────────────────────
    #
    # A module -> module edge is an import declaration, and Python import
    # cycles between packages are the framework's least legible failure: the
    # app raises a partially initialised module deep in DI wiring, far from
    # the two frames that caused it. Catching it on the canvas is the entire
    # value of drawing imports.
    slug_by_id = {
        node.id: node.config.name
        for node in module_nodes
        if isinstance(node.config, ModuleConfig)
    }
    for edge in document.edges:
        if (
            edge.src in slug_by_id
            and edge.dst in slug_by_id
            and slug_by_id[edge.src] == slug_by_id[edge.dst]
        ):
            diagnostics.append(
                Diagnostic(
                    node_id=edge.src,
                    severity=DiagnosticSeverity.ERROR,
                    code="module.self_import",
                    message=f"Module {slug_by_id[edge.src]!r} imports itself",
                    hint="A module's own members are always visible to it.",
                )
            )

    # One derivation, shared with the emitter: a graph cannot validate as
    # acyclic and then emit a cycle.
    imports = module_import_graph(document)

    for cycle in _import_cycles(imports):
        diagnostics.append(
            Diagnostic(
                node_id=next(
                    (nid for nid, slug in slug_by_id.items() if slug == cycle[0]),
                    None,
                ),
                severity=DiagnosticSeverity.ERROR,
                code="module.import_cycle",
                message="Module imports form a cycle: " + " -> ".join(cycle),
                hint=(
                    "Move the shared piece into a third module both can "
                    "import, mark it is_global, or invert one dependency "
                    "with an exported protocol."
                ),
            )
        )

    # ── informational ────────────────────────────────────────────────────
    members = {n.module for n in document.nodes if n.module is not None}
    for node in module_nodes:
        if isinstance(node.config, ModuleConfig) and node.config.name not in members:
            diagnostics.append(
                Diagnostic(
                    node_id=node.id,
                    severity=DiagnosticSeverity.INFO,
                    code="module.empty",
                    message=f"Module {node.config.name!r} has no members",
                    hint=(
                        "This is legal -- it matches `lexigram new module` -- "
                        "and generates an empty bounded context."
                    ),
                )
            )

    return diagnostics
