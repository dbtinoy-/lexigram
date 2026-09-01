"""ProjectWriter — thin orchestrator over core codegen StagedGeneration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace as dc_replace
from pathlib import Path
import shutil
import subprocess
from typing import Any

from lexigram.builder.gen.cli_bridge import load_generator
from lexigram.builder.gen.emitters.apikey_emitter import (
    emit_api_key_repository,
    emit_api_keys_auth_module,
    emit_api_keys_migration,
    merged_api_key_scopes,
)
from lexigram.builder.gen.emitters.audit_emitter import (
    emit_audit_migration,
    emit_audit_repository,
)
from lexigram.builder.gen.emitters.audit_postprocess import ControllerAuditHooks
from lexigram.builder.gen.emitters.context import pascal_entity, table_name
from lexigram.builder.gen.emitters.contract_postprocess import (
    ContractBinding,
    ControllerContract,
    emit_contract_module,
)
from lexigram.builder.gen.emitters.email_emitter import (
    emit_email_module,
    emit_emails_init,
    emit_mailer_helper,
)
from lexigram.builder.gen.emitters.entity_emitter import (
    crud_test_filename,
    emit_crud_test,
)
from lexigram.builder.gen.emitters.file_upload_emitter import (
    emit_upload_controller,
    emit_upload_storage,
)
from lexigram.builder.gen.emitters.flag_postprocess import ControllerFlagGates
from lexigram.builder.gen.emitters.guard_postprocess import (
    ControllerGuards,
    emit_rate_limit_middleware,
    emit_rate_limit_module,
)
from lexigram.builder.gen.emitters.scaffold import emit_scaffold_files
from lexigram.builder.gen.emitters.search_emitter import (
    effective_engine as effective_engine_local,
)
from lexigram.builder.gen.emitters.search_emitter import (
    emit_search_controller,
    emit_search_migration,
    emit_search_repository,
)
from lexigram.builder.gen.emitters.validator_emitter import (
    emit_validator_module,
)
from lexigram.builder.gen.node_generators import (
    ENTITY_ATTACHED,
    ReconcileContext,
    autofix_for,
    dest_for,
    entity_attached_extra_kwargs,
    reconcile_text,
    staging_dirs,
)
from lexigram.builder.graph.models import (
    ApiClientConfig,
    ApiKeyGroupConfig,
    AppSettingsConfig,
    AuditLogConfig,
    AuthConfig,
    AuthPolicyConfig,
    ChannelConfig,
    ContractConfig,
    CqrsMessageConfig,
    CronConfig,
    DataLoaderConfig,
    EmailTemplateConfig,
    EntityConfig,
    EventConfig,
    EventHandlerConfig,
    ExceptionFilterConfig,
    FeatureFlagConfig,
    FileUploadConfig,
    GraphDocument,
    GraphNode,
    InterceptorConfig,
    JobConfig,
    MetricConfig,
    MiddlewareConfig,
    ProjectionConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
    SagaConfig,
    SearchIndexConfig,
    StorageDriverConfig,
    ValidatedGraph,
    ValidatorConfig,
    WebhookConfig,
)
from lexigram.codegen import GenerationResult, GeneratorBase
from lexigram.contracts.cli.generators import (
    CollisionPolicy,
    GenerationOptions,
    snake_case,
)

__all__ = ["ProjectWriter"]

# Generated projects live at <playground>/projects/<app>. The framework is
# vendored as a git submodule at <playground>/lexigram, so from a generated
# project's root two parent hops reach the playground root and the framework
# is at "../../lexigram". Absolute framework-root overrides (tmp-dir runs)
# take precedence in _relative_monorepo_root().
_FRAMEWORK_REPO_REL = "../../lexigram"


class ProjectWriter(GeneratorBase):
    """Writes a generated project tree for a validated graph.

    Stages every emitted file under ``<projects_root>/<app_name>`` and
    commits atomically with the OVERWRITE policy (regeneration wins —
    the canvas graph is the source of truth).

    Args:
        projects_root: Directory holding one subdirectory per project.
        post_process: When True, run ``ruff format`` over the committed
            project after a successful write (skipped when ruff absent).
        framework_root: Absolute framework-checkout override for generated
            ``[tool.uv.sources]`` (tmp-dir runs); None keeps the
            deterministic relative form.
    """

    def __init__(
        self,
        projects_root: Path,
        *,
        post_process: bool = False,
        framework_root: str | None = None,
        pypi_sources: bool = False,
    ) -> None:
        super().__init__(output_dir=projects_root)
        self._post_process = post_process
        self._framework_root = framework_root
        # Container/cloud mode: generated projects depend on published
        # PyPI packages instead of local editable paths.
        self._pypi_sources = pypi_sources

    def write_project(
        self,
        graph: ValidatedGraph,
        *,
        on_file: Callable[[str, int, int], None] | None = None,
    ) -> GenerationResult:
        """Emit, stage, and commit the full project for *graph*."""
        settings_config = graph.settings().config
        assert isinstance(settings_config, AppSettingsConfig)
        app_name = settings_config.app_name

        entities: list[EntityConfig] = []
        for node in graph.entities():
            assert isinstance(node.config, EntityConfig)
            entities.append(node.config)
        middlewares: list[MiddlewareConfig] = []
        for node in graph.document.nodes:
            if node.kind == "middleware" and isinstance(node.config, MiddlewareConfig):
                middlewares.append(node.config)
        # Stable stack order: explicit order hint, then name.
        middlewares.sort(key=lambda m: (m.order, m.name))
        crons: list[CronConfig] = []
        for node in graph.document.nodes:
            if node.kind == "cron" and isinstance(node.config, CronConfig):
                crons.append(node.config)
        crons.sort(key=lambda c: c.name)
        webhooks: list[WebhookConfig] = []
        for node in graph.document.nodes:
            if node.kind == "webhook" and isinstance(node.config, WebhookConfig):
                webhooks.append(node.config)
        webhooks.sort(key=lambda w: w.name)
        enabled_webhooks = [w for w in webhooks if w.enabled]
        jobs: list[JobConfig] = []
        for node in graph.document.nodes:
            if node.kind == "job" and isinstance(node.config, JobConfig):
                jobs.append(node.config)
        jobs.sort(key=lambda j: j.name)
        enabled_jobs = [j for j in jobs if j.enabled]
        channels: list[ChannelConfig] = []
        for node in graph.document.nodes:
            if node.kind == "realtime_channel" and isinstance(
                node.config, ChannelConfig
            ):
                channels.append(node.config)
        events: list[EventConfig] = []
        for node in graph.document.nodes:
            if node.kind == "event" and isinstance(node.config, EventConfig):
                events.append(node.config)
        events.sort(key=lambda e: e.name)
        enabled_events = [e for e in events if e.enabled]
        event_handlers: list[EventHandlerConfig] = []
        for node in graph.document.nodes:
            if node.kind == "event_handler" and isinstance(
                node.config, EventHandlerConfig
            ):
                event_handlers.append(node.config)
        event_handlers.sort(key=lambda h: h.name)
        enabled_handlers = [h for h in event_handlers if h.enabled]
        cqrs_messages: list[CqrsMessageConfig] = []
        for node in graph.document.nodes:
            if node.kind in ("command", "query") and isinstance(
                node.config, CqrsMessageConfig
            ):
                cqrs_messages.append(node.config)
        cqrs_messages.sort(key=lambda m: (m.side, m.name))
        enabled_cqrs = [m for m in cqrs_messages if m.enabled]
        projections: list[ProjectionConfig] = []
        for node in graph.document.nodes:
            if node.kind == "projection" and isinstance(
                node.config, ProjectionConfig
            ):
                projections.append(node.config)
        projections.sort(key=lambda p: p.name)
        enabled_projections = [p for p in projections if p.enabled]
        metrics: list[MetricConfig] = []
        for node in graph.document.nodes:
            if node.kind == "metric" and isinstance(node.config, MetricConfig):
                metrics.append(node.config)
        metrics.sort(key=lambda m: m.name)
        enabled_metrics = [m for m in metrics if m.enabled]
        sagas: list[SagaConfig] = []
        for node in graph.document.nodes:
            if node.kind == "saga" and isinstance(node.config, SagaConfig):
                sagas.append(node.config)
        sagas.sort(key=lambda s: s.name)
        enabled_sagas = [s for s in sagas if s.enabled]
        interceptors: list[InterceptorConfig] = []
        for node in graph.document.nodes:
            if node.kind == "interceptor" and isinstance(node.config, InterceptorConfig):
                interceptors.append(node.config)
        interceptors.sort(key=lambda s: s.name)
        enabled_interceptors = [s for s in interceptors if s.enabled]
        dataloaders: list[DataLoaderConfig] = []
        for node in graph.document.nodes:
            if node.kind == "dataloader" and isinstance(node.config, DataLoaderConfig):
                dataloaders.append(node.config)
        dataloaders.sort(key=lambda s: s.name)
        enabled_dataloaders = [s for s in dataloaders if s.enabled]
        auth_policies: list[AuthPolicyConfig] = []
        for node in graph.document.nodes:
            if node.kind == "auth_policy" and isinstance(node.config, AuthPolicyConfig):
                auth_policies.append(node.config)
        auth_policies.sort(key=lambda s: s.name)
        enabled_auth_policies = [s for s in auth_policies if s.enabled]
        api_clients: list[ApiClientConfig] = []
        for node in graph.document.nodes:
            if node.kind == "api_client" and isinstance(node.config, ApiClientConfig):
                api_clients.append(node.config)
        api_clients.sort(key=lambda c: c.name)
        enabled_api_clients = [c for c in api_clients if c.enabled]
        storage_drivers: list[StorageDriverConfig] = []
        for node in graph.document.nodes:
            if node.kind == "storage_driver" and isinstance(
                node.config, StorageDriverConfig
            ):
                storage_drivers.append(node.config)
        storage_drivers.sort(key=lambda c: c.name)
        enabled_storage_drivers = [c for c in storage_drivers if c.enabled]
        filters: list[ExceptionFilterConfig] = []
        for node in graph.document.nodes:
            if node.kind == "exception_filter" and isinstance(
                node.config, ExceptionFilterConfig
            ):
                filters.append(node.config)
        filters.sort(key=lambda f: f.name)
        enabled_filters = [f for f in filters if f.enabled]
        flags: list[FeatureFlagConfig] = []
        for node in graph.document.nodes:
            if node.kind == "feature_flag" and isinstance(
                node.config, FeatureFlagConfig
            ):
                flags.append(node.config)
        flags.sort(key=lambda f: f.name)
        enabled_flags = [f for f in flags if f.enabled]
        # Guard-chain nodes (auth / role / rate_limit). These were validated
        # but inert before Workstream B; they now emit definition scaffolds
        # and decorate the controllers of the routes wired to them.
        auths: list[AuthConfig] = []
        for node in graph.document.nodes:
            if node.kind == "auth" and isinstance(node.config, AuthConfig):
                auths.append(node.config)
        auths.sort(key=lambda a: a.name)
        roles: list[RoleConfig] = []
        for node in graph.document.nodes:
            if node.kind == "role" and isinstance(node.config, RoleConfig):
                roles.append(node.config)
        roles.sort(key=lambda r: r.name)
        rate_limits: list[RateLimitConfig] = []
        for node in graph.document.nodes:
            if node.kind == "rate_limit" and isinstance(
                node.config, RateLimitConfig
            ):
                rate_limits.append(node.config)
        rate_limits.sort(key=lambda r: r.name)
        # API-key groups (nodes plan N4.2): screen-managed kind — no edges,
        # first enabled group defines header/prefix, scope union across all.
        api_key_groups: list[ApiKeyGroupConfig] = []
        for node in graph.document.nodes:
            if node.kind == "api_key_group" and isinstance(
                node.config, ApiKeyGroupConfig
            ):
                api_key_groups.append(node.config)
        api_key_groups.sort(key=lambda g: g.name)
        enabled_api_key_groups = [g for g in api_key_groups if g.enabled]
        # Email templates (nodes plan N4.3): screen-managed kind (Emails
        # modal) — one Mailable module per enabled template plus shared
        # mailer/init modules; triggers are documentation-only in v1.x.
        email_templates: list[EmailTemplateConfig] = []
        for node in graph.document.nodes:
            if node.kind == "email_template" and isinstance(
                node.config, EmailTemplateConfig
            ):
                email_templates.append(node.config)
        email_templates.sort(key=lambda t: t.name)
        enabled_email_templates = [t for t in email_templates if t.enabled]
        # Contract nodes (Workstream C): builder-side Pydantic DTO modules
        # whose models swap into wired controllers' payloads/responses.
        search_indexes: list[SearchIndexConfig] = []
        for node in graph.document.nodes:
            if isinstance(
                node.config, SearchIndexConfig
            ) and node.kind == "search_index":
                search_indexes.append(node.config)
        search_indexes.sort(key=lambda si: si.name)
        file_uploads: list[FileUploadConfig] = []
        for node in graph.document.nodes:
            if isinstance(
                node.config, FileUploadConfig
            ) and node.kind == "file_upload":
                file_uploads.append(node.config)
        file_uploads.sort(key=lambda fu: fu.name)
        validators: list[ValidatorConfig] = []
        for node in graph.document.nodes:
            if isinstance(node.config, ValidatorConfig) and node.kind == "validator":
                validators.append(node.config)
        validators.sort(key=lambda v: v.name)
        contracts: list[ContractConfig] = []
        for node in graph.document.nodes:
            if node.kind == "contract" and isinstance(
                node.config, ContractConfig
            ):
                contracts.append(node.config)
        contracts.sort(key=lambda c: c.name)
        channels.sort(key=lambda c: c.name)
        enabled_channels = [c for c in channels if c.enabled]
        # Normalise each channel's mount path to /ws/<name> when unspecified.
        enabled_channels = [
            c
            if c.path
            else ChannelConfig(
                name=c.name,
                path=f"/ws/{c.name}",
                enabled=c.enabled,
                description=c.description,
            )
            for c in enabled_channels
        ]
        by_id = {n.id: n for n in graph.document.nodes}
        # Trigger → jobs wiring: webhook/cron nodes fan out to connected jobs.
        jobs_by_trigger: dict[str, list[str]] = {}
        enabled_job_names = {j.name for j in enabled_jobs}
        for edge in graph.document.edges:
            src = by_id.get(edge.src)
            dst = by_id.get(edge.dst)
            if src is None or dst is None or not isinstance(dst.config, JobConfig):
                continue
            if dst.config.name not in enabled_job_names:
                continue
            if src.kind in ("webhook", "cron") and isinstance(
                src.config, WebhookConfig | CronConfig
            ):
                jobs_by_trigger.setdefault(src.config.name, []).append(dst.config.name)
        ops_by_entity: dict[str, list[str]] = {}
        style_by_entity: dict[str, str] = {}
        path_by_entity: dict[str, str] = {}
        entity_by_name: dict[str, EntityConfig] = {}
        # Guard wiring: route node id -> the guard nodes its edges target.
        auth_by_route: dict[str, AuthConfig] = {}
        roles_by_route: dict[str, list[RoleConfig]] = {}
        rate_limits_by_route: dict[str, list[RateLimitConfig]] = {}
        # Contract wiring: route node id -> the contract its edge targets.
        contracts_by_route: dict[str, ContractConfig] = {}
        # Flag gating: route node id -> the enabled flags its edges target.
        flags_by_route: dict[str, list[FeatureFlagConfig]] = {}
        for edge in graph.document.edges:
            src = by_id.get(edge.src)
            dst = by_id.get(edge.dst)
            if src is None or dst is None or src.kind != "route":
                continue
            if dst.kind == "auth" and isinstance(dst.config, AuthConfig):
                auth_by_route.setdefault(src.id, dst.config)
            elif dst.kind == "role" and isinstance(dst.config, RoleConfig):
                roles_by_route.setdefault(src.id, []).append(dst.config)
            elif dst.kind == "rate_limit" and isinstance(
                dst.config, RateLimitConfig
            ):
                rate_limits_by_route.setdefault(src.id, []).append(dst.config)
            elif dst.kind == "contract" and isinstance(
                dst.config, ContractConfig
            ):
                contracts_by_route.setdefault(src.id, dst.config)
            elif (
                dst.kind == "feature_flag"
                and isinstance(dst.config, FeatureFlagConfig)
                and dst.config.enabled
            ):
                flags_by_route.setdefault(src.id, []).append(dst.config)
        # Guarded ops/roles per served entity (drives controller decoration).
        guard_auth_ops_by_entity: dict[str, set[str]] = {}
        guard_roles_by_entity: dict[str, dict[str, set[str]]] = {}
        # Contract bindings per served entity (op -> binding; first wiring
        # wins when several wired routes serve the same op).
        contract_bindings_by_entity: dict[str, dict[str, ContractBinding]] = {}
        # Flag gates per served entity (flag key -> guarded ops).
        flag_gates_by_entity: dict[str, dict[str, set[str]]] = {}
        # Validator rules per entity name (entity -> validator edges; the
        # entity node's own config is the authoritative field list).
        validator_rules_by_entity: dict[str, list[tuple[str, str]]] = {}
        # rate-limit name -> the path prefixes of its wired routes.
        paths_by_rate_limit: dict[str, set[str]] = {}
        for route_node in graph.routes():
            assert isinstance(route_node.config, RouteConfig)
            route_path = (route_node.config.path_prefix or "").strip()
            if route_path and route_node.id in rate_limits_by_route:
                for rl in rate_limits_by_route[route_node.id]:
                    paths_by_rate_limit.setdefault(rl.name, set()).add(route_path)
            # The entity this route serves: the first edge landing on an
            # entity node (guard edges may precede it in the edge list).
            dst_id = next(
                (
                    e.dst
                    for e in graph.document.edges
                    if e.src == route_node.id
                    and (dst_node := by_id.get(e.dst)) is not None
                    and isinstance(dst_node.config, EntityConfig)
                ),
                None,
            )
            if dst_id is None:
                continue
            dst_config = by_id[dst_id].config
            assert isinstance(dst_config, EntityConfig)
            bucket = ops_by_entity.setdefault(dst_config.name, [])
            bucket.extend(op for op in route_node.config.ops if op not in bucket)
            entity_by_name[dst_config.name] = dst_config
            if route_node.config.style == "resource":
                style_by_entity[dst_config.name] = "resource"
            # First explicit path prefix wins; blank/None falls back to the
            # table name below.
            prefix = (route_node.config.path_prefix or "").strip()
            if prefix and dst_config.name not in path_by_entity:
                path_by_entity[dst_config.name] = prefix
            # A route wired to an auth or role node guards its ops (roles
            # imply authentication — "role -> auth collapses to the guard").
            if route_node.id in auth_by_route:
                guard_auth_ops_by_entity.setdefault(
                    dst_config.name, set()
                ).update(route_node.config.ops)
            for role in roles_by_route.get(route_node.id, []):
                op_roles = guard_roles_by_entity.setdefault(dst_config.name, {})
                for op in route_node.config.ops:
                    op_roles.setdefault(op, set()).add(role.name)
            # A route wired to an enabled contract binds its ops to that
            # contract's models (Workstream C).
            contract = contracts_by_route.get(route_node.id)
            if contract is not None and contract.enabled:
                op_bindings = contract_bindings_by_entity.setdefault(
                    dst_config.name, {}
                )
                for op in route_node.config.ops:
                    op_bindings.setdefault(op, ContractBinding(contract=contract))
            # Routes wired to enabled flags gate their ops (nodes plan N2.1):
            # several flags on one route gate conjunctively.
            for flag in flags_by_route.get(route_node.id, []):
                flag_gates_by_entity.setdefault(dst_config.name, {}).setdefault(
                    flag.name, set()
                ).update(route_node.config.ops)

        # Entity-attached validators (entity -> validator edges): merge the
        # wired validators' rules per entity (later nodes win field clashes).
        validator_cfg_by_name = {v.name: v for v in validators}
        for e in graph.document.edges:
            src_node = by_id.get(e.src)
            dst_node = by_id.get(e.dst)
            if (
                src_node is None
                or dst_node is None
                or not isinstance(src_node.config, EntityConfig)
                or not isinstance(dst_node.config, ValidatorConfig)
                or dst_node.config.name not in validator_cfg_by_name
            ):
                continue
            cfg = validator_cfg_by_name[dst_node.config.name]
            if cfg.enabled:
                validator_rules_by_entity.setdefault(
                    src_node.config.name, []
                ).extend(cfg.rules)

        # Entity-attached generators (entity -> <node> edges): each node kind
        # maps to a framework verb in ENTITY_ATTACHED (service / seeder /
        # error / cache). Collect (entity, node_config) targets per kind in a
        # single registry-driven pass — adding a generator means adding an
        # ENTITY_ATTACHED entry, not another edge loop.
        attached: dict[str, list[tuple[EntityConfig, Any]]] = {
            kind: [] for kind in ENTITY_ATTACHED
        }
        seen_attached: dict[str, set[str]] = {kind: set() for kind in ENTITY_ATTACHED}
        for edge in graph.document.edges:
            src = by_id.get(edge.src)
            dst = by_id.get(edge.dst)
            if src is None or dst is None or src.kind != "entity":
                continue
            if dst.kind not in ENTITY_ATTACHED:
                continue
            if not isinstance(src.config, EntityConfig) or not getattr(
                dst.config, "enabled", True
            ):
                continue
            if src.config.name in seen_attached[dst.kind]:
                continue
            seen_attached[dst.kind].add(src.config.name)
            attached[dst.kind].append((src.config, dst.config))

        def attached_entities(kind: str) -> list[EntityConfig]:
            return [ent for ent, _cfg in attached[kind]]

        def attached_cfgs(kind: str) -> list[Any]:
            return [cfg for _ent, cfg in attached[kind]]

        service_entities = attached_entities("service")
        seeder_entities = attached_entities("seeder")
        error_cfgs = attached_cfgs("error")
        cache_cfgs = attached_cfgs("cache")
        graphql_cfgs = attached_cfgs("graphql")
        health_cfgs = attached_cfgs("health")

        files: dict[str, str] = {}
        # Entity-attached search indexes (entity -> search_index edges):
        # merge fields/boost across index nodes per entity (first engine wins).
        search_cfg_by_entity: dict[str, SearchIndexConfig] = {}
        for e in graph.document.edges:
            src_node = by_id.get(e.src)
            dst_node = by_id.get(e.dst)
            if (
                src_node is None
                or dst_node is None
                or not isinstance(src_node.config, EntityConfig)
                or not isinstance(dst_node.config, SearchIndexConfig)
                or not dst_node.config.enabled
            ):
                continue
            scfg = dst_node.config
            existing = search_cfg_by_entity.get(src_node.config.name)
            if existing is None:
                search_cfg_by_entity[src_node.config.name] = SearchIndexConfig(
                    name=scfg.name,
                    entity=src_node.config.name,
                    fields=scfg.fields,
                    engine=scfg.engine,
                    boost=dict(scfg.boost or {}),
                    description=scfg.description,
                )
            else:
                merged_fields = tuple(
                    dict.fromkeys((*existing.fields, *scfg.fields))
                )
                merged_boost = dict(existing.boost or {})
                merged_boost.update(scfg.boost or {})
                search_cfg_by_entity[src_node.config.name] = SearchIndexConfig(
                    name=existing.name,
                    entity=existing.entity,
                    fields=merged_fields,
                    engine=existing.engine,
                    boost=merged_boost,
                    description=existing.description,
                )

        # Search-index emission (nodes plan N3.2): migration + repository +
        # search controller per wired entity. Migration revisions chain so
        # alembic sees a single head.
        search_entities_sorted = sorted(search_cfg_by_entity)
        # Entity migrations use chained "001"/"002"/... revisions (see the
        # model/repository/migration loop below); the search migrations must
        # chain onto that head so alembic keeps a single history line.
        search_prev_rev: str | None = f"{len(entities):03d}" if entities else None
        for idx, entity_name in enumerate(search_entities_sorted):
            search_cfg = search_cfg_by_entity[entity_name]
            route_path = self._route_path(entity_name, path_by_entity)
            if effective_engine_local(search_cfg) == "fts":
                revision = f"b{idx + 1:04d}_{entity_name}_search_fts"
                files[f"migrations/versions/{revision}.py"] = (
                    emit_search_migration(
                        entity_name,
                        search_cfg,
                        revision=revision,
                        prev_revision=search_prev_rev,
                    )
                )
                search_prev_rev = revision
            files[f"src/app/repositories/{entity_name}_search_repository.py"] = (
                emit_search_repository(entity_name, search_cfg)
            )
            files[f"src/app/controllers/{entity_name}_search_controller.py"] = (
                emit_search_controller(entity_name, route_path)
            )

        # Audit-log emission (nodes plan N4.1): entity-attached. The first
        # enabled audit_log wired to each entity defines its trail; multiple
        # audit nodes on one entity merge their op subsets (union).
        audit_cfg_by_entity: dict[str, AuditLogConfig] = {}
        for e in graph.document.edges:
            src_node = by_id.get(e.src)
            dst_node = by_id.get(e.dst)
            if (
                src_node is None
                or dst_node is None
                or not isinstance(src_node.config, EntityConfig)
                or not isinstance(dst_node.config, AuditLogConfig)
                or not dst_node.config.enabled
            ):
                continue
            acfg = dst_node.config
            audit_existing = audit_cfg_by_entity.get(src_node.config.name)
            if audit_existing is None:
                audit_cfg_by_entity[src_node.config.name] = AuditLogConfig(
                    name=acfg.name,
                    entity=src_node.config.name,
                    operations=tuple(
                        op
                        for op in ("create", "update", "delete")
                        if op in acfg.operations
                    ),
                    capture_fields=acfg.capture_fields,
                    exclude_fields=acfg.exclude_fields,
                    capture_request_meta=acfg.capture_request_meta,
                    retention_days=acfg.retention_days,
                    description=acfg.description,
                )
            else:
                audit_cfg_by_entity[src_node.config.name] = AuditLogConfig(
                    name=audit_existing.name,
                    entity=audit_existing.entity,
                    operations=tuple(
                        dict.fromkeys(
                            (*audit_existing.operations, *acfg.operations)
                        )
                    ),
                    capture_fields=tuple(
                        dict.fromkeys(
                            (*audit_existing.capture_fields, *acfg.capture_fields)
                        )
                    ),
                    exclude_fields=tuple(
                        dict.fromkeys(
                            (*audit_existing.exclude_fields, *acfg.exclude_fields)
                        )
                    ),
                    capture_request_meta=(
                        audit_existing.capture_request_meta
                        or acfg.capture_request_meta
                    ),
                    retention_days=min(
                        audit_existing.retention_days, acfg.retention_days
                    ),
                    description=audit_existing.description or acfg.description,
                )

        # Migration revisions chain: entity table -> search FTS -> audit
        # table, so alembic keeps a single history line.
        audit_entities_sorted = sorted(audit_cfg_by_entity)
        audit_prev_rev = search_prev_rev
        for idx, entity_name in enumerate(audit_entities_sorted):
            audit_cfg = audit_cfg_by_entity[entity_name]
            revision = f"b{idx + 1:04d}_{entity_name}_audit_log"
            files[f"migrations/versions/{revision}.py"] = emit_audit_migration(
                entity_name,
                audit_cfg,
                revision=revision,
                prev_revision=audit_prev_rev,
            )
            audit_prev_rev = revision
            files[f"src/app/repositories/{entity_name}_audit_repository.py"] = (
                emit_audit_repository(entity_name, audit_cfg)
            )

        # API-key emission (nodes plan N4.2): screen-driven. One shared
        # surface per app — the migration chains after the audit head.
        if enabled_api_key_groups:
            primary = enabled_api_key_groups[0]
            scopes = merged_api_key_scopes(enabled_api_key_groups)
            revision = "b0001_api_keys"
            files[f"migrations/versions/{revision}.py"] = emit_api_keys_migration(
                revision=revision,
                prev_revision=audit_prev_rev,
            )
            audit_prev_rev = revision
            files["src/app/repositories/api_key_repository.py"] = (
                emit_api_key_repository()
            )
            files["src/app/auth/__init__.py"] = (
                "# generated by lexigram-builder - do not edit\n"
            )
            files["src/app/auth/api_keys.py"] = emit_api_keys_auth_module(
                primary, scopes
            )

        # Email emission (nodes plan N4.3): screen-driven. One Mailable
        # module per enabled template + shared mailer/init modules.
        if enabled_email_templates:
            files["src/app/emails/__init__.py"] = emit_emails_init(
                enabled_email_templates
            )
            files["src/app/emails/mailer.py"] = emit_mailer_helper()
            for template in enabled_email_templates:
                files[f"src/app/emails/{template.name}.py"] = (
                    emit_email_module(template)
                )

        # File-upload emission (nodes plan N3.3): route-attached. The
        # (route -> file_upload) edge binds an upload config to a route; the
        # upload endpoint mounts at that route's entity path + /upload.
        # First enabled binding per route wins; unwired nodes are inert.
        upload_cfg_by_route: dict[str, FileUploadConfig] = {}
        if any(fu.enabled for fu in file_uploads):
            for edge in graph.document.edges:
                src_node = by_id.get(edge.src)
                dst_node = by_id.get(edge.dst)
                if (
                    src_node is None
                    or dst_node is None
                    or not isinstance(src_node.config, RouteConfig)
                    or not isinstance(dst_node.config, FileUploadConfig)
                    or not dst_node.config.enabled
                    or src_node.id in upload_cfg_by_route
                ):
                    continue
                upload_cfg_by_route[src_node.id] = dst_node.config
        driver_type_by_upload: dict[str, str] = {}
        for edge in graph.document.edges:
            src_node = by_id.get(edge.src)
            dst_node = by_id.get(edge.dst)
            if (
                src_node is None
                or dst_node is None
                or src_node.kind != "file_upload"
                or dst_node.kind != "storage_driver"
                or not isinstance(src_node.config, FileUploadConfig)
                or not isinstance(dst_node.config, StorageDriverConfig)
                or not dst_node.config.enabled
            ):
                continue
            driver_type_by_upload[src_node.config.name] = dst_node.config.driver_type
        _DRIVER_STORAGE = {
            "s3": "s3",
            "gcs": "gcs",
            "azure": "azure_blob",
            "local": "local",
            "custom": "local",
        }
        for route_id, ucfg in list(upload_cfg_by_route.items()):
            mapped = _DRIVER_STORAGE.get(driver_type_by_upload.get(ucfg.name, ""), ucfg.storage)
            if mapped != ucfg.storage:
                upload_cfg_by_route[route_id] = dc_replace(ucfg, storage=mapped)
        upload_entities: dict[str, FileUploadConfig] = {}
        for route_id, upload_cfg in upload_cfg_by_route.items():
            route_node = by_id[route_id]
            route_cfg = route_node.config
            assert isinstance(route_cfg, RouteConfig)
            # Resolve the entity this route serves (drives the mount path).
            entity_name = ""
            for edge in graph.document.edges:
                if edge.src != route_id:
                    continue
                target = by_id.get(edge.dst)
                if target and isinstance(target.config, EntityConfig):
                    entity_name = target.config.name
                    break
            if entity_name:
                route_path = self._route_path(entity_name, path_by_entity)
            else:
                prefix = (route_cfg.path_prefix or "").strip()
                if not prefix:
                    continue  # no mount path can be derived; nothing to emit
                route_path = "/" + prefix.strip("/")
            # First upload per entity wins (same rule as the search merge).
            if entity_name in upload_entities:
                continue
            upload_entities[entity_name] = upload_cfg
            files[f"src/app/uploads/{upload_cfg.name}_upload_storage.py"] = (
                emit_upload_storage(entity_name, upload_cfg)
            )
            files[f"src/app/controllers/{upload_cfg.name}_upload_controller.py"] = (
                emit_upload_controller(entity_name, route_path, upload_cfg)
            )
        if upload_entities:
            files["src/app/uploads/__init__.py"] = (
                "# Generated by lexigram-builder. Do not edit; regenerate instead.\n"
            )

        files.update(
            emit_scaffold_files(
                app_name,
                entities,
                [(RouteConfig(ops=()), entity_by_name[name]) for name in ops_by_entity],
                relative_root=self._relative_monorepo_root(),
                structure=settings_config.structure,
                pypi_sources=self._uses_pypi_sources(),
                extra_dependencies=self._extra_dependencies(
                    entities, uploads=bool(upload_entities)
                ),
                api_clients=bool(enabled_api_clients),
                storage_drivers=bool(enabled_storage_drivers),
                middlewares=middlewares,
                crons=tuple(c for c in crons if c.enabled),
                webhooks=tuple(enabled_webhooks),
                jobs=tuple(enabled_jobs),
                jobs_by_trigger=dict(jobs_by_trigger),
                channels=tuple(enabled_channels),
                services=tuple(service_entities),
                seeders=tuple(seeder_entities),
                filters=tuple(enabled_filters),
                errors=tuple(error_cfgs),
                caches=tuple(cache_cfgs),
                graphql=tuple(graphql_cfgs),
                health_checks=tuple(health_cfgs),
                events=tuple(enabled_events),
                event_handlers=tuple(_resolve_handlers(enabled_handlers, graph.document, by_id)),
                cqrs_messages=tuple(_resolve_cqrs(enabled_cqrs, graph.document, by_id)),
                projections=tuple(
                    _resolve_projections(enabled_projections, graph.document, by_id)
                ),
                metrics=tuple(enabled_metrics),
                sagas=tuple(enabled_sagas),
                flags=tuple(enabled_flags),
                auths=tuple(auths),
                api_key_groups=tuple(enabled_api_key_groups),
                email_templates=tuple(enabled_email_templates),
                roles=tuple(roles),
                policies=tuple(rate_limits),
                rate_limited=bool(rate_limits),
                search_entities=tuple(search_entities_sorted),
                audit_repositories=tuple(audit_entities_sorted),
                upload_controllers=tuple(
                    (name, cfg.name)
                    for name, cfg in sorted(upload_entities.items())
                ),
            )
        )
        assert all(isinstance(e, EntityConfig) for e in entities)

        # Data-layer artifacts come from the framework's own CLI
        # generators (model / repository / migration) via cli_bridge —
        # sorted entities chain their alembic revisions.
        staging_root = Path(self.output_dir) / ".staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        gen_dirs = staging_dirs(staging_root)

        # Custom middleware components (framework web `middleware` generator).
        for mw in middlewares:
            load_generator("middleware", output_dir=gen_dirs["middleware"]).generate(
                mw.name,
                doc=f"Generated {mw.type} middleware.",
                force=True,
            )

        # Scheduled background tasks (framework tasks `task` generator, @scheduled).
        enabled_crons = [c for c in crons if c.enabled]
        for cron in enabled_crons:
            load_generator("task", output_dir=gen_dirs["task"]).generate(
                cron.name,
                schedule=cron.schedule,
                doc=cron.description or f"Scheduled task {cron.name}.",
                force=True,
            )

        # Plain background jobs (same generator, no schedule -> @task). These
        # run only when a connected trigger enqueues them.
        cron_names = {c.name for c in enabled_crons}
        for job in enabled_jobs:
            if job.name in cron_names:
                continue  # a cron with the same name already emitted it
            load_generator("task", output_dir=gen_dirs["task"]).generate(
                job.name,
                doc=job.description or f"Background job {job.name}.",
                force=True,
            )

        # Inbound webhook triggers: the framework webhook generator emits a
        # payload + HMAC-verification handler; we wrap it in a thin framework
        # Controller that mounts a POST route (see _emit_webhook_controller).
        for hook in enabled_webhooks:
            load_generator("webhook", output_dir=gen_dirs["webhook"]).generate(
                hook.name,
                doc=hook.description or f"Webhook {hook.name}.",
                force=True,
            )

        # Realtime channels: the framework websocket generator emits an
        # AbstractWebSocketHandler; a late-boot provider registers it as a
        # container singleton and appends a WebSocketRoute (see WS-1 in
        # docs/LEXIGRAM_FRAMEWORK_BUGS.md — standalone handlers are not
        # auto-discovered by the web router).
        for channel in enabled_channels:
            load_generator("websocket", output_dir=gen_dirs["websocket"]).generate(
                channel.name,
                doc=channel.description or f"Realtime channel {channel.name}.",
                force=True,
            )

        prev_rev: str | None = None
        for idx, entity in enumerate(sorted(entities, key=lambda e: e.name), start=1):
            rev_id = f"{idx:03d}"
            fields_str = _fields_str(entity)
            # The framework migration template hardcodes id/created_at/
            # updated_at columns but its generator (unlike the model
            # generator's RESERVED_FIELDS) does not filter them from the
            # field list — declaring any of them would emit a duplicate
            # column and break the smoke tests. Pre-filter here (framework
            # bug; see docs/LEXIGRAM_FRAMEWORK_BUGS.md).
            migration_fields_str = ",".join(
                part
                for part in fields_str.split(",")
                if part and part.split(":", 1)[0] not in _MIGRATION_RESERVED
            )
            table = table_name(entity.name)
            load_generator("model", output_dir=gen_dirs["model"]).generate(
                entity.name,
                fields_str=fields_str,
                force=True,
            )
            load_generator("repository", output_dir=gen_dirs["repository"]).generate(
                entity.name,
                fields_str=fields_str,
                table_name=table,
                force=True,
            )
            load_generator("migration", output_dir=gen_dirs["migration"]).generate(
                entity.name,
                fields_str=migration_fields_str,
                rev_id=rev_id,
                prev_rev=prev_rev,
                table_name=table,
                force=True,
            )
            prev_rev = rev_id

        # Entity-attached generators (service / seeder / error / cache), driven
        # by the ENTITY_ATTACHED registry. Each target invokes its framework
        # verb with the entity name, its fields, and any node-config extras.
        for kind, verb in ENTITY_ATTACHED.items():
            for entity, node_cfg in sorted(attached[kind], key=lambda t: t[0].name):
                kwargs: dict[str, Any] = {
                    "fields_str": _fields_str(entity),
                    "force": True,
                }
                kwargs.update(entity_attached_extra_kwargs(kind, node_cfg))
                load_generator(verb, output_dir=gen_dirs[verb]).generate(
                    entity.name,
                    **kwargs,
                )

        # Global exception filters (framework web `exception_filter` generator).
        for flt in enabled_filters:
            load_generator(
                "exception_filter", output_dir=gen_dirs["exception_filter"]
            ).generate(
                flt.name,
                exception_type=flt.exception_type,
                status_code=flt.status_code,
                doc=flt.description or f"Exception filter {flt.name}.",
                force=True,
            )

        # Event handlers (framework lexigram-events `event_handler` generator).
        # These in-process subscribers are subscribed to their wired event by a
        # late-boot registration provider emitted by the scaffold.
        resolved_handlers = _resolve_handlers(
            enabled_handlers, graph.document, by_id
        )

        # Domain events (framework lexigram-events `event` generator). Each
        # event is a standalone node carrying its payload fields; the app
        # wires EventsModule so handlers can subscribe via the event bus. A
        # handler naming a fallback event without a wired event node still
        # needs that event's module to exist for the subscription import.
        event_payloads: dict[str, str] = {}
        for evt in enabled_events:
            fields_str = ",".join(f"{name}:{typ}" for name, typ in evt.payload)
            event_payloads[evt.name] = fields_str
        for handler in resolved_handlers:
            event_payloads.setdefault(handler.event, "")
        for event_name, fields_str in sorted(event_payloads.items()):
            load_generator("event", output_dir=gen_dirs["event"]).generate(
                event_name,
                fields_str=fields_str or None,
                force=True,
            )

        for handler in resolved_handlers:
            load_generator(
                "event_handler", output_dir=gen_dirs["event_handler"]
            ).generate(
                handler.name,
                force=True,
            )

        # CQRS commands and queries (framework lexigram-events `command` /
        # `query` generators). Each emits message + handler in one module;
        # the scaffold registers the handler on the matching bus at boot.
        resolved_cqrs = _resolve_cqrs(enabled_cqrs, graph.document, by_id)
        for msg in resolved_cqrs:
            fields_str = ",".join(f"{name}:{typ}" for name, typ in msg.fields)
            load_generator(msg.side, output_dir=gen_dirs[msg.side]).generate(
                msg.name,
                fields_str=fields_str or None,
                force=True,
            )

        # Read-model projections (framework lexigram-events `projection`
        # generator). A late-boot provider builds a ProjectionManager and
        # subscribes it to the event bus for each projection's events.
        resolved_projections = _resolve_projections(
            enabled_projections, graph.document, by_id
        )
        for projection in resolved_projections:
            load_generator(
                "projection", output_dir=gen_dirs["projection"]
            ).generate(
                projection.name,
                doc=projection.description or None,
                force=True,
            )

        # Application metrics (framework lexigram-monitor `metric`
        # generator). The generated <Name>Metric is a user-edited scaffold;
        # its presence only ensures MonitorModule is configured.
        for metric in enabled_metrics:
            load_generator("metric", output_dir=gen_dirs["metric"]).generate(
                metric.name,
                force=True,
            )

        for saga in enabled_sagas:
            load_generator("saga", output_dir=gen_dirs["saga"]).generate(
                saga.name,
                force=True,
            )

        for interceptor in enabled_interceptors:
            load_generator(
                "interceptor", output_dir=gen_dirs["interceptor"]
            ).generate(
                interceptor.name,
                doc=interceptor.description or None,
                force=True,
            )

        for loader in enabled_dataloaders:
            load_generator(
                "dataloader", output_dir=gen_dirs["dataloader"]
            ).generate(
                loader.name,
                key_type=loader.key_type,
                force=True,
            )

        for client in enabled_api_clients:
            load_generator("api_client", output_dir=gen_dirs["api_client"]).generate(
                client.name,
                auth=client.auth_type,
                force=True,
            )
        for driver in enabled_storage_drivers:
            load_generator(
                "storage_driver", output_dir=gen_dirs["storage_driver"]
            ).generate(
                driver.name,
                driver_type=driver.driver_type,
                force=True,
            )

        # Feature flags (framework lexigram-features `feature_flag`
        # generator). Each enabled flag emits one <Name>Flag definition
        # module; the scaffold registers FeatureFlagsModule (seeding the
        # canonical keys) only when at least one flag exists.
        for flag in enabled_flags:
            load_generator("feature_flag", output_dir=gen_dirs["feature_flag"]).generate(
                flag.name,
                force=True,
            )

        # Guard scaffolds (framework lexigram-auth generators): one
        # <Name>AuthGuard credential-check definition per auth node, one
        # <Name>Guard (RoleGuard variant) per role node. Enforcement on the
        # wired routes happens in the controller decoration below.
        for auth in auths:
            load_generator("auth_guard", output_dir=gen_dirs["auth_guard"]).generate(
                auth.name,
                force=True,
            )
        for role in roles:
            load_generator("guard", output_dir=gen_dirs["guard"]).generate(
                role.name,
                type="role",
                force=True,
            )
        for policy in enabled_auth_policies:
            load_generator(
                "auth_policy", output_dir=gen_dirs["auth_policy"]
            ).generate(
                policy.name,
                force=True,
            )

        # Rate-limit policies + enforcement middleware (nodes plan N2.2 —
        # the framework has no per-route throttle primitive). The policy
        # module records the path prefixes of the routes wired to the node
        # (empty → documented placeholder); the middleware enforces it.
        for limit in rate_limits:
            wired = tuple(sorted(paths_by_rate_limit.get(limit.name, set())))
            files[
                f"src/app/policies/{limit.name}_rate_limit.py"
            ] = emit_rate_limit_module(limit, paths=wired, doc=limit.description)

        # Contract DTO modules (builder-side — the framework has no
        # contract generator; Workstream C). Wired controllers import the
        # contract models in place of the auto-derived <Entity>Create/
        # Update DTOs (controller decoration below).
        # The enforcement middleware for those policies (nodes plan N2.2):
        # imports the policy constants, so definition and enforcement cannot
        # drift. Registered in app.py via the scaffold's middleware list.
        if rate_limits:
            files["src/app/middleware/rate_limit.py"] = emit_rate_limit_middleware(
                [
                    (limit, tuple(sorted(paths_by_rate_limit.get(limit.name, set()))))
                    for limit in rate_limits
                ]
            )

        enabled_contracts = [c for c in contracts if c.enabled]
        for contract in enabled_contracts:
            files[f"src/app/contracts/{contract.name}.py"] = (
                emit_contract_module(contract)
            )
        if enabled_contracts:
            files["src/app/contracts/__init__.py"] = (
                "# generated by lexigram-builder - do not edit\n"
            )

        # Validator constraint modules (nodes plan N3.1) — one per entity
        # with wired, enabled validators.
        for entity_name in sorted(validator_rules_by_entity):
            rules = tuple(validator_rules_by_entity[entity_name])
            if not rules:
                continue
            merged = ValidatorConfig(
                name=f"validate_{entity_name}", rules=rules
            )
            files[f"src/app/validators/{entity_name}.py"] = (
                emit_validator_module(entity_name, merged)
            )
            files["src/app/validators/__init__.py"] = (
                "# generated by lexigram-builder - do not edit\n"
            )

        for entity_name in sorted(ops_by_entity):
            entity_cfg = entity_by_name[entity_name]
            route_path = self._route_path(entity_name, path_by_entity)
            if style_by_entity.get(entity_name) == "resource":
                # ResourceGenerator writes output_dir/controllers/*.py
                load_generator(
                    "resource", output_dir=gen_dirs["controller"].parent
                ).generate(
                    entity_name,
                    fields_str=_fields_str(entity_cfg),
                    force=True,
                )
            else:
                load_generator("controller", output_dir=gen_dirs["controller"]).generate(
                    entity_name,
                    fields_str=_fields_str(entity_cfg),
                    path=route_path,
                    force=True,
                )

        # Stage → destination mapping and per-file reconciliation are entirely
        # data-driven from VERB_SPECS (see gen/node_generators.py). Adding a
        # generator-backed node adds a registry entry rather than another
        # branch here.
        reconcile_ctx = ReconcileContext(
            entity_by_stem={entity.name: entity for entity in entities},
            channel_by_stem={c.name: c for c in enabled_channels},
            event_handler_by_stem={
                f"{snake_case(h.name)}_handler": h for h in resolved_handlers
            },
            projection_by_stem={
                f"{snake_case(p.name)}_projection": p
                for p in _resolve_projections(
                    enabled_projections, graph.document, by_id
                )
            },
            guards_by_entity={
                entity_name: ControllerGuards(
                    ops=frozenset(
                        guard_auth_ops_by_entity.get(entity_name, set())
                        - set(guard_roles_by_entity.get(entity_name, {}))
                    ),
                    roles_by_op={
                        op: tuple(sorted(roles))
                        for op, roles in guard_roles_by_entity.get(
                            entity_name, {}
                        ).items()
                    },
                )
                for entity_name in (
                    set(guard_auth_ops_by_entity) | set(guard_roles_by_entity)
                )
            },
            contracts_by_entity={
                entity_name: ControllerContract(
                    by_op=dict(op_bindings),
                )
                for entity_name, op_bindings in contract_bindings_by_entity.items()
            },
            flag_gates_by_entity={
                entity_name: ControllerFlagGates(
                    by_op={
                        op: tuple(sorted(
                            flag
                            for flag, ops in gates.items()
                            if op in ops
                        ))
                        for op in sorted({
                            op for ops in gates.values() for op in ops
                        })
                    }
                )
                for entity_name, gates in flag_gates_by_entity.items()
            },
            audit_by_entity={
                entity_name: ControllerAuditHooks(
                    ops=frozenset(
                        audit_cfg_by_entity[entity_name].operations
                    ),
                    repo_class=(
                        f"{pascal_entity(entity_name)}AuditRepository"
                    ),
                    repo_module=(
                        f"app.repositories.{entity_name}_audit_repository"
                    ),
                )
                for entity_name in audit_entities_sorted
            },
        )
        for verb, gen_dir in gen_dirs.items():
            dest_sub = dest_for(verb)
            do_autofix = autofix_for(verb)
            for produced in sorted(gen_dir.glob("*.py")):
                text = produced.read_text(encoding="utf-8")
                text = reconcile_text(verb, text, produced, reconcile_ctx)
                if do_autofix:
                    text = _ruff_autofix_text(text, produced.name)
                files[f"{dest_sub}/{produced.name}"] = text
        shutil.rmtree(staging_root, ignore_errors=True)

        # HTTP smoke tests only for entities that actually have routes.
        routed_names = set(ops_by_entity)
        for entity in entities:
            if entity.name in routed_names:
                rel = crud_test_filename(entity)
                files[rel] = emit_crud_test(
                    entity,
                    ops=frozenset(ops_by_entity[entity.name]),
                    path=self._route_path(entity.name, path_by_entity),
                )

        app_prefix = f"{app_name}/"
        _prune_stale_generated(
            Path(self.output_dir) / app_name,
            keep={f"{app_prefix}{rel}" for rel in files},
        )

        staged_paths = sorted(files)
        total = len(staged_paths)
        for index, rel_path in enumerate(staged_paths, start=1):
            self.stage(app_prefix + rel_path, files[rel_path])
            if on_file is not None:
                on_file(rel_path, index, total)

        result = self.commit(GenerationOptions(policy=CollisionPolicy.OVERWRITE))
        if self._post_process:
            self._ruff_format(Path(self.output_dir) / app_name)
        return self.finalize(result)

    @staticmethod
    def _route_path(entity_name: str, path_by_entity: dict[str, str]) -> str:
        """Resolve the API base path for an entity's controller.

        Prefers an explicit route ``path_prefix`` from the canvas; otherwise
        the framework generator's default pluralized table name.
        """
        prefix = path_by_entity.get(entity_name)
        if prefix:
            return "/" + prefix.strip("/")
        return f"/{table_name(entity_name)}"

    def _uses_pypi_sources(self) -> bool:
        return self._pypi_sources

    @staticmethod
    def _extra_dependencies(
        entities: list[EntityConfig], uploads: bool = False
    ) -> tuple[str, ...]:
        """Pinned extra deps required by the field types used in *entities*.

        The framework's Pydantic models rely on optional extras (e.g.
        ``EmailStr`` needs ``email-validator``); surface them in the
        generated pyproject so ``uv sync`` pulls them and the generated
        app imports cleanly.
        """
        field_types = {f.type for entity in entities for f in entity.fields}
        deps: list[str] = []
        if "email" in field_types:
            deps.append("email-validator>=2.0.0")
        if uploads:
            # starlette's request.form() multipart parsing needs it.
            deps.append("python-multipart>=0.0.9")
        return tuple(deps)

    def _relative_monorepo_root(self) -> str:
        """Path prefix for generated [tool.uv.sources].

        Absolute when a framework root override is supplied (tmp-dir runs);
        otherwise the deterministic relative form used by golden snapshots.
        """
        return self._framework_root or _FRAMEWORK_REPO_REL

    def _ruff_format(self, project_dir: Path) -> None:
        """Lint-fix and format the generated project in place.

        Framework templates (notably ``lexigram-tasks``' task template, see
        TASK-3 in docs/LEXIGRAM_FRAMEWORK_BUGS.md) emit code with auto-fixable
        lint issues: trailing whitespace in Jinja blanks (W293), unsorted
        imports (I001), ``dict.get(k, None)`` (SIM910), and dead parameter
        locals (F841). ``ruff format`` only handles whitespace, so run
        ``ruff check --fix`` first. ``--unsafe-fixes`` is intentional: the
        code is freshly generated (no hand edits to protect) and the only
        unsafe fix that fires is removing a provably-unused local.
        """
        ruff = shutil.which("ruff")
        if ruff is None:
            return
        for argv in (
            [ruff, "check", "--fix", "--unsafe-fixes", "."],
            [ruff, "format", "."],
        ):
            subprocess.run(  # noqa: S603 - fixed argv, no shell
                argv,
                cwd=project_dir,
                check=False,
                capture_output=True,
                timeout=60,
            )


# Reserved by the framework migration template (always emitted there).
_MIGRATION_RESERVED = frozenset({"id", "created_at", "updated_at"})


def _fields_str(entity: EntityConfig) -> str:
    parts = []
    for field in entity.fields:
        part = f"{field.name}:{field.type}"
        if field.nullable:
            part += "?"
        parts.append(part)
    return ",".join(parts)


def _resolve_cqrs(
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


def _resolve_projections(
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
        if node.kind != "projection" or not isinstance(
            node.config, ProjectionConfig
        ):
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


def _resolve_handlers(
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


def _ruff_autofix_text(text: str, filename: str) -> str:
    """Run ``ruff check --fix`` on *text* in-memory, returning fixed source.

    Used for generators whose templates emit auto-fixable lint noise (unused
    imports, modern-type style). Falls back to the original text if ruff is
    unavailable or fails, so generation never depends on the linter being
    installed.
    """
    import sys

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--fix", "-", "--stdin-filename", filename],
            input=text,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return text
    # ruff writes the fixed source to stdout even when it reports fixes made.
    return proc.stdout if proc.stdout else text


def _prune_stale_generated(project_dir: Path, *, keep: set[str]) -> None:
    """Delete previously generated files that are no longer produced."""
    managed_roots = [
        project_dir / "src" / "app" / "controllers",
        project_dir / "src" / "app" / "repositories",
        project_dir / "src" / "app" / "models",
        project_dir / "src" / "app" / "middleware",
        project_dir / "src" / "app" / "tasks",
        project_dir / "src" / "app" / "webhooks",
        project_dir / "src" / "app" / "graphql",
        project_dir / "src" / "app" / "healthchecks",
        project_dir / "src" / "app" / "events",
        project_dir / "src" / "app" / "handlers",
        project_dir / "src" / "app" / "commands",
        project_dir / "src" / "app" / "queries",
        project_dir / "src" / "app" / "projections",
        project_dir / "src" / "app" / "metrics",
        project_dir / "src" / "app" / "sagas",
        project_dir / "src" / "app" / "interceptors",
        project_dir / "src" / "app" / "clients",
        project_dir / "src" / "app" / "storage" / "backends",
        project_dir / "src" / "app" / "features",
        project_dir / "src" / "app" / "guards",
        project_dir / "src" / "app" / "auth",
        project_dir / "src" / "app" / "emails",
        project_dir / "src" / "app" / "validators",
        project_dir / "src" / "app" / "uploads",
        project_dir / "src" / "app" / "policies",
        project_dir / "src" / "app" / "contracts",
        project_dir / "src" / "app" / "di",
        project_dir / "migrations" / "versions",
        project_dir / "tests",
    ]
    prefix_len = len(str(project_dir)) + 1
    for root in managed_roots:
        if not root.is_dir():
            continue
        for child in sorted(root.rglob("*.py")):
            rel = str(child)[prefix_len:]
            if rel not in keep:
                child.unlink(missing_ok=True)
