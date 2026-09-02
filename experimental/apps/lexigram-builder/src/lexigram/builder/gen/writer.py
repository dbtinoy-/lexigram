"""ProjectWriter — thin orchestrator over core codegen StagedGeneration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace as dc_replace
from pathlib import Path
import shutil
from typing import Any

from lexigram.builder.gen.cli_bridge import load_generator
from lexigram.builder.gen.edge_resolution import (
    resolve_cqrs,
    resolve_handlers,
    resolve_projections,
)
from lexigram.builder.gen.emitted import AttributionLedger, EmittedFile
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
from lexigram.builder.gen.formatting import format_project
from lexigram.builder.gen.layout import DEFAULT_LAYOUT, WriterLayout
from lexigram.builder.gen.modular import (
    Placement,
    commit_staged,
    emit_modular_project,
    sole,
)
from lexigram.builder.gen.node_generators import (
    ENTITY_ATTACHED,
    STANDALONE_NODE_KWARGS,
    ReconcileContext,
    dest_for,
    entity_attached_extra_kwargs,
)
from lexigram.builder.gen.packaging import FRAMEWORK_REPO_REL, extra_dependencies
from lexigram.builder.gen.pruning import prune_stale_generated
from lexigram.builder.gen.staging import StagingArea
from lexigram.builder.graph.palette import KIND_MODULE
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
        layout: WriterLayout | None = None,
    ) -> None:
        super().__init__(output_dir=projects_root)
        self._post_process = post_process
        # Structure-aware path authority. Defaults to the minimal layout so
        # existing golden trees stay byte-identical.
        self._layout = layout or DEFAULT_LAYOUT
        self._ledger: AttributionLedger | None = None
        self._framework_root = framework_root
        # Container/cloud mode: generated projects depend on published
        # PyPI packages instead of local editable paths.
        self._pypi_sources = pypi_sources

    @property
    def emitted(self) -> tuple[EmittedFile, ...]:
        """Attribution records from the most recent :meth:`write_project`."""
        return self._ledger.records if self._ledger is not None else ()

    def files_by_node(self) -> dict[str, list[str]]:
        """``{node_id: [paths]}`` for the most recent write.

        Recorded as files were produced (task L4), so it stays correct
        under any project structure -- unlike deriving it from paths.
        """
        return self._ledger.files_by_node() if self._ledger is not None else {}

    def write_project(
        self,
        graph: ValidatedGraph,
        *,
        on_file: Callable[[str, int, int, EmittedFile | None], None] | None = None,
    ) -> GenerationResult:
        """Emit, stage, and commit the full project for *graph*."""
        # L4: attribution is recorded as files are produced, not deduced from
        # their paths afterwards. Config objects are the same instances the
        # document holds, so identity maps them back to their node without
        # touching any of the extraction loops below.
        ledger = AttributionLedger()
        self._ledger = ledger
        # The graph decides the layout, not the constructor: this writer
        # outlives any one project (see ``WriterLayout.for_settings``).
        # ``mods`` is that layout's import map -- "shop_api.repositories"
        # unscoped, "shop_api.modules.sales.repositories" scoped -- never a
        # hardcoded stem.
        settings_config = graph.settings().config
        assert isinstance(settings_config, AppSettingsConfig)
        app_name = settings_config.app_name
        self._layout = WriterLayout.for_settings(settings_config)
        mods = self._layout.module_names()
        # Bounded contexts are a fact about this graph, not a project mode:
        # a graph that declares modules gets module packages and a
        # discovering composition root, and one that does not gets neither.
        # This is what lets a project start flat and grow into contexts
        # without relocating a single file that was already correct.
        has_modules = any(node.kind == KIND_MODULE for node in graph.document.nodes)
        # A component then has no single destination -- `order`
        # belongs to sales, `invoice` to billing, and both are repositories.
        # `place` is the layout's missing half: it answers "which context
        # owns this config's files?" so destinations and import roots are
        # resolved together instead of each caller guessing (MODULAR-1/2).
        place = Placement.of(graph, self._layout)
        node_id_by_config = {id(n.config): n.id for n in graph.document.nodes}

        def owner(config: object | None) -> str | None:
            """Node id that owns *config*, or None for synthesised configs."""
            return None if config is None else node_id_by_config.get(id(config))

        entities: list[EntityConfig] = []
        for node in graph.entities():
            assert isinstance(node.config, EntityConfig)
            entities.append(node.config)
        # Some files are named after an entity but caused by another node:
        # `order`'s search repository exists because a Search Index node was
        # drawn, yet it is a repository *of order* and belongs wherever
        # order does. Placing it by its entity keeps a bounded context's
        # persistence in one package instead of scattering it by cause.
        entity_cfg_by_name: dict[str, EntityConfig] = {e.name: e for e in entities}
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
        validator_owner_by_entity: dict[str, str] = {}
        # rate-limit name -> the path prefixes of its wired routes.
        paths_by_rate_limit: dict[str, set[str]] = {}
        route_owner_by_entity: dict[str, str] = {}
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
            # First route wins, matching the previous attribution order.
            route_owner_by_entity.setdefault(dst_config.name, route_node.id)
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
                # Rules from several validators merge into one module, so
                # the first wired validator node owns the result.
                validator_owner_by_entity.setdefault(
                    src_node.config.name, dst_node.id
                )
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
        # Like audit, merged search configs are rebuilt, so identity cannot
        # map them back; remember the first wired node explicitly.
        search_owner_by_entity: dict[str, str] = {}
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
            search_owner_by_entity.setdefault(src_node.config.name, dst_node.id)
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
            search_owner = search_owner_by_entity.get(entity_name)
            if effective_engine_local(search_cfg) == "fts":
                revision = f"b{idx + 1:04d}_{entity_name}_search_fts"
                ledger.record(
                    f"migrations/versions/{revision}.py",
                    node_id=search_owner,
                    verb="migration",
                )
                files[f"migrations/versions/{revision}.py"] = (
                    emit_search_migration(
                        entity_name,
                        search_cfg,
                        revision=revision,
                        prev_revision=search_prev_rev,
                    )
                )
                search_prev_rev = revision
            search_entity = entity_cfg_by_name.get(entity_name)
            search_repo_dest = place.dest("repository", search_entity)
            ledger.record(
                f"{search_repo_dest}/{entity_name}_search_repository.py",
                node_id=search_owner,
                verb="repository",
            )
            files[
                f"{search_repo_dest}/{entity_name}_search_repository.py"
            ] = (
                emit_search_repository(entity_name, search_cfg)
            )
            search_ctl_dest = place.dest("controller", search_entity)
            ledger.record(
                f"{search_ctl_dest}/{entity_name}_search_controller.py",
                node_id=search_owner,
                verb="controller",
            )
            files[
                f"{search_ctl_dest}/{entity_name}_search_controller.py"
            ] = (
                emit_search_controller(
                    entity_name, route_path, place.imports(search_entity)
                )
            )

        # Audit-log emission (nodes plan N4.1): entity-attached. The first
        # enabled audit_log wired to each entity defines its trail; multiple
        # audit nodes on one entity merge their op subsets (union).
        audit_cfg_by_entity: dict[str, AuditLogConfig] = {}
        # Merged audit configs are freshly constructed, so identity cannot
        # map them back to a node; remember the first wired one explicitly.
        audit_owner_by_entity: dict[str, str] = {}
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
            audit_owner_by_entity.setdefault(src_node.config.name, dst_node.id)
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
            audit_owner = audit_owner_by_entity.get(entity_name)
            ledger.record(
                f"migrations/versions/{revision}.py",
                node_id=audit_owner,
                verb="migration",
            )
            files[f"migrations/versions/{revision}.py"] = emit_audit_migration(
                entity_name,
                audit_cfg,
                revision=revision,
                prev_revision=audit_prev_rev,
            )
            audit_prev_rev = revision
            audit_repo_dest = place.dest(
                "repository", entity_cfg_by_name.get(entity_name)
            )
            ledger.record(
                f"{audit_repo_dest}/{entity_name}_audit_repository.py",
                node_id=audit_owner,
                verb="repository",
            )
            files[
                f"{audit_repo_dest}/{entity_name}_audit_repository.py"
            ] = (
                emit_audit_repository(entity_name, audit_cfg)
            )

        # API-key emission (nodes plan N4.2): screen-driven. One shared
        # surface per app — the migration chains after the audit head.
        if enabled_api_key_groups:
            primary = enabled_api_key_groups[0]
            scopes = merged_api_key_scopes(enabled_api_key_groups)
            revision = "b0001_api_keys"
            # The API-key surface is app-global; the primary group owns it.
            api_key_owner = owner(primary)
            for rel in (
                f"migrations/versions/{revision}.py",
                f"{dest_for('repository', self._layout)}/api_key_repository.py",
                self._layout.pkg("auth", "__init__.py"),
                self._layout.pkg("auth", "api_keys.py"),
            ):
                ledger.record(rel, node_id=api_key_owner)
            files[f"migrations/versions/{revision}.py"] = emit_api_keys_migration(
                revision=revision,
                prev_revision=audit_prev_rev,
            )
            audit_prev_rev = revision
            files[f"{dest_for('repository', self._layout)}/api_key_repository.py"] = (
                emit_api_key_repository()
            )
            files[self._layout.pkg("auth", "__init__.py")] = (
                "# generated by lexigram-builder - do not edit\n"
            )
            files[self._layout.pkg("auth", "api_keys.py")] = emit_api_keys_auth_module(
                primary, scopes, mods
            )

        # Email emission (nodes plan N4.3): screen-driven. One Mailable
        # module per enabled template + shared mailer/init modules.
        if enabled_email_templates:
            email_owner = owner(enabled_email_templates[0])
            for rel in (
                self._layout.pkg("emails", "__init__.py"),
                self._layout.pkg("emails", "mailer.py"),
            ):
                ledger.record(rel, node_id=email_owner)
            files[self._layout.pkg("emails", "__init__.py")] = emit_emails_init(
                enabled_email_templates, mods
            )
            files[self._layout.pkg("emails", "mailer.py")] = emit_mailer_helper()
            for template in enabled_email_templates:
                ledger.record(
                    self._layout.pkg("emails", f"{template.name}.py"),
                    node_id=owner(template),
                )
                files[self._layout.pkg("emails", f"{template.name}.py")] = (
                    emit_email_module(template)
                )

        # File-upload emission (nodes plan N3.3): route-attached. The
        # (route -> file_upload) edge binds an upload config to a route; the
        # upload endpoint mounts at that route's entity path + /upload.
        # First enabled binding per route wins; unwired nodes are inert.
        upload_cfg_by_route: dict[str, FileUploadConfig] = {}
        upload_owner_by_route: dict[str, str] = {}
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
                # The storage-driver remap below rebuilds this config, so
                # remember its node now while identity still holds.
                upload_owner_by_route[src_node.id] = dst_node.id
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
            upload_owner = upload_owner_by_route.get(route_id)
            storage_path = place.pkg(
                "uploads",
                f"{upload_cfg.name}_upload_storage.py",
                config=upload_cfg,
            )
            controller_path = (
                f"{place.dest('controller', upload_cfg)}"
                f"/{upload_cfg.name}_upload_controller.py"
            )
            ledger.record(storage_path, node_id=upload_owner)
            ledger.record(
                controller_path, node_id=upload_owner, verb="controller"
            )
            files[storage_path] = emit_upload_storage(entity_name, upload_cfg)
            files[controller_path] = emit_upload_controller(
                entity_name, route_path, upload_cfg, place.imports(upload_cfg)
            )
        for _slug, group in place.group(list(upload_entities.values())):
            files[place.pkg("uploads", "__init__.py", config=sole(group))] = (
                "# Generated by lexigram-builder. Do not edit; regenerate instead.\n"
            )

        files.update(
            emit_scaffold_files(
                app_name,
                entities,
                [(RouteConfig(ops=()), entity_by_name[name]) for name in ops_by_entity],
                relative_root=self._monorepo_root(),
                has_modules=has_modules,
                placement=place,
                profiles=settings_config.profiles,
                layout=self._layout,
                pypi_sources=self._pypi_sources,
                extra_dependencies=extra_dependencies(
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
                event_handlers=tuple(resolve_handlers(enabled_handlers, graph.document, by_id)),
                cqrs_messages=tuple(resolve_cqrs(enabled_cqrs, graph.document, by_id)),
                projections=tuple(
                    resolve_projections(enabled_projections, graph.document, by_id)
                ),
                metrics=tuple(enabled_metrics),
                sagas=tuple(enabled_sagas),
                flags=tuple(enabled_flags),
                auths=tuple(auths),
                api_key_groups=tuple(enabled_api_key_groups),
                email_templates=tuple(enabled_email_templates),
                roles=tuple(roles),
                policies=tuple(enabled_auth_policies),
                rate_limited=bool(rate_limits),
                search_entities=tuple(search_entities_sorted),
                audit_repositories=tuple(audit_entities_sorted),
                upload_controllers=tuple(
                    (name, cfg.name, place.imports(cfg)["uploads"])
                    for name, cfg in sorted(upload_entities.items())
                ),
            )
        )
        assert all(isinstance(e, EntityConfig) for e in entities)

        # Data-layer artifacts come from the framework's own CLI
        # generators (model / repository / migration) via cli_bridge —
        # sorted entities chain their alembic revisions.
        staging_root = Path(self.output_dir) / ".staging"
        # Clear it first, not just on the way out. Attribution credits a
        # node with whatever *appears* in a staging dir, so a file left
        # behind by a run that crashed before its cleanup is invisible to
        # the next run -- it was already there. That used to cost only a
        # missing ledger entry; under modular, attribution also decides
        # destinations, so a poisoned staging dir turns into "no Module
        # node owns this file" on a graph that is perfectly correct.
        shutil.rmtree(staging_root, ignore_errors=True)
        # Staging is shaped like the destination and anchored as a project,
        # so a generator resolves its own imports from where it is standing
        # instead of emitting bare package names for the writer to repair
        # afterwards (OQ-L5). `generating` hands out that directory and
        # credits whatever appears in it to the node that asked.
        staging = StagingArea(
            staging_root, layout=self._layout, placement=place
        )
        generating = staging.generating

        # Custom middleware components (framework web `middleware` generator).
        for mw in middlewares:
            with generating("middleware", owner(mw)) as staged_dir:
                load_generator(
                    "middleware", output_dir=staged_dir
                ).generate(
                    mw.name,
                    doc=f"Generated {mw.type} middleware.",
                    force=True,
                )

        # Scheduled background tasks (framework tasks `task` generator, @scheduled).
        enabled_crons = [c for c in crons if c.enabled]
        for cron in enabled_crons:
            with generating("task", owner(cron)) as staged_dir:
                load_generator("task", output_dir=staged_dir).generate(
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
            with generating("task", owner(job)) as staged_dir:
                load_generator("task", output_dir=staged_dir).generate(
                    job.name,
                    doc=job.description or f"Background job {job.name}.",
                    force=True,
                )

        # Inbound webhook triggers: the framework webhook generator emits a
        # payload + HMAC-verification handler; we wrap it in a thin framework
        # Controller that mounts a POST route (see _emit_webhook_controller).
        for hook in enabled_webhooks:
            with generating("webhook", owner(hook)) as staged_dir:
                load_generator("webhook", output_dir=staged_dir).generate(
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
            with generating("websocket", owner(channel)) as staged_dir:
                load_generator("websocket", output_dir=staged_dir).generate(
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
            with generating("model", owner(entity)) as staged_dir:
                load_generator("model", output_dir=staged_dir).generate(
                    entity.name,
                    fields_str=fields_str,
                    force=True,
                )
            with generating("repository", owner(entity)) as staged_dir:
                load_generator(
                    "repository", output_dir=staged_dir
                ).generate(
                    entity.name,
                    fields_str=fields_str,
                    table_name=table,
                    force=True,
                )
            with generating("migration", owner(entity)) as staged_dir:
                load_generator("migration", output_dir=staged_dir).generate(
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
                with generating(verb, owner(node_cfg)) as staged_dir:
                    load_generator(verb, output_dir=staged_dir).generate(
                        entity.name,
                        **kwargs,
                    )

        # Global exception filters (framework web `exception_filter`).
        for flt in enabled_filters:
            with generating("exception_filter", owner(flt)) as staged_dir:
                load_generator(
                    "exception_filter", output_dir=staged_dir
                ).generate(
                    flt.name,
                    **STANDALONE_NODE_KWARGS["exception_filter"](flt),
                    force=True,
                )

        # Event handlers (framework lexigram-events `event_handler` generator).
        # These in-process subscribers are subscribed to their wired event by a
        # late-boot registration provider emitted by the scaffold.
        resolved_handlers = resolve_handlers(
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
        # Edge resolution rebuilds handler/message/projection configs, so
        # identity no longer maps them to their node -- the name does, and
        # a duplicate name is already a validation error.
        handler_owner_by_name = {h.name: owner(h) for h in enabled_handlers}
        event_owner_by_name = {e.name: owner(e) for e in enabled_events}
        for handler in resolved_handlers:
            # An event a handler merely names has no node; the handler is
            # the only reason its module exists, so the handler owns it.
            event_owner_by_name.setdefault(
                handler.event, handler_owner_by_name.get(handler.name)
            )
        for event_name, fields_str in sorted(event_payloads.items()):
            with generating("event", event_owner_by_name.get(event_name)) as staged_dir:
                load_generator("event", output_dir=staged_dir).generate(
                    event_name,
                    fields_str=fields_str or None,
                    force=True,
                )

        for handler in resolved_handlers:
            with generating(
                "event_handler", handler_owner_by_name.get(handler.name)
            ) as staged_dir:
                load_generator(
                    "event_handler", output_dir=staged_dir
                ).generate(
                    handler.name,
                    force=True,
                )

        # CQRS commands and queries (framework lexigram-events `command` /
        # `query` generators). Each emits message + handler in one module;
        # the scaffold registers the handler on the matching bus at boot.
        resolved_cqrs = resolve_cqrs(enabled_cqrs, graph.document, by_id)
        cqrs_owner_by_name = {(m.side, m.name): owner(m) for m in enabled_cqrs}
        for msg in resolved_cqrs:
            fields_str = ",".join(f"{name}:{typ}" for name, typ in msg.fields)
            with generating(
                msg.side, cqrs_owner_by_name.get((msg.side, msg.name))
            ) as staged_dir:
                load_generator(msg.side, output_dir=staged_dir).generate(
                    msg.name,
                    fields_str=fields_str or None,
                    force=True,
                )

        # Read-model projections (framework lexigram-events `projection`
        # generator). A late-boot provider builds a ProjectionManager and
        # subscribes it to the event bus for each projection's events.
        resolved_projections = resolve_projections(
            enabled_projections, graph.document, by_id
        )
        projection_owner_by_name = {
            p.name: owner(p) for p in enabled_projections
        }
        for projection in resolved_projections:
            with generating(
                "projection", projection_owner_by_name.get(projection.name)
            ) as staged_dir:
                load_generator(
                    "projection", output_dir=staged_dir
                ).generate(
                    projection.name,
                    doc=projection.description or None,
                    force=True,
                )

        # One-config-one-module node runs, driven by
        # STANDALONE_NODE_KWARGS so a new kind adds a row rather than
        # another loop -- and cannot be added without attribution.
        standalone_nodes: list[tuple[str, list[Any]]] = [
            ("metric", list(enabled_metrics)),
            ("saga", list(enabled_sagas)),
            ("interceptor", list(enabled_interceptors)),
            ("dataloader", list(enabled_dataloaders)),
            ("api_client", list(enabled_api_clients)),
            ("storage_driver", list(enabled_storage_drivers)),
        ]
        # Feature flags seed FeatureFlagsModule's canonical keys; guard
        # scaffolds are the credential check (auth) and role variants, with
        # enforcement decorated onto the wired controllers below.
        standalone_nodes += [
            ("feature_flag", list(enabled_flags)),
            ("auth_guard", list(auths)),
            ("guard", list(roles)),
            ("auth_policy", list(enabled_auth_policies)),
        ]
        for verb, configs in standalone_nodes:
            for config in configs:
                with generating(verb, owner(config)) as staged_dir:
                    load_generator(verb, output_dir=staged_dir).generate(
                        config.name,
                        **STANDALONE_NODE_KWARGS[verb](config),
                        force=True,
                    )

        # Rate-limit policies + enforcement middleware (nodes plan N2.2 —
        # the framework has no per-route throttle primitive). The policy
        # module records the path prefixes of the routes wired to the node
        # (empty → documented placeholder); the middleware enforces it.
        # The policy module sits in the middleware package, not `policies/`:
        # `policies/` is where the framework's `auth_policy` generator writes
        # and is module-local under modular, while a rate limit is
        # cross-cutting (its kind maps to `middleware`). Borrowing that shelf
        # made a shared middleware import a bounded context's package -- the
        # boundary inverted -- and left a rate limit with nowhere to live in
        # a modular app.
        for limit in rate_limits:
            wired = tuple(sorted(paths_by_rate_limit.get(limit.name, set())))
            files[
                f"{dest_for('middleware', self._layout)}/"
                f"{limit.name}_rate_limit.py"
            ] = emit_rate_limit_module(limit, paths=wired, doc=limit.description)

        # Contract DTO modules (builder-side — the framework has no
        # contract generator; Workstream C). Wired controllers import the
        # contract models in place of the auto-derived <Entity>Create/
        # Update DTOs (controller decoration below).
        # The enforcement middleware for those policies (nodes plan N2.2):
        # imports the policy constants, so definition and enforcement cannot
        # drift. Registered in app.py via the scaffold's middleware list.
        if rate_limits:
            files[
                f"{dest_for('middleware', self._layout)}/rate_limit.py"
            ] = emit_rate_limit_middleware(
                [
                    (limit, tuple(sorted(paths_by_rate_limit.get(limit.name, set()))))
                    for limit in rate_limits
                ],
                self._layout,
            )

        enabled_contracts = [c for c in contracts if c.enabled]
        for contract in enabled_contracts:
            ledger.record(
                self._layout.pkg("contracts", f"{contract.name}.py"),
                node_id=owner(contract),
            )
            files[self._layout.pkg("contracts", f"{contract.name}.py")] = (
                emit_contract_module(contract)
            )
        if enabled_contracts:
            files[self._layout.pkg("contracts", "__init__.py")] = (
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
            # Rules from several validator nodes merge into one module, so
            # the config is rebuilt and identity is gone; the node that
            # caused the file is still recorded, and that is enough to place
            # it (validators are module-local under modular).
            validator_node = validator_owner_by_entity.get(entity_name)
            validator_path = place.pkg(
                "validators", f"{entity_name}.py", config=validator_node
            )
            ledger.record(validator_path, node_id=validator_node)
            files[validator_path] = emit_validator_module(entity_name, merged)
            files[place.pkg("validators", "__init__.py", config=validator_node)] = (
                "# generated by lexigram-builder - do not edit\n"
            )

        for entity_name in sorted(ops_by_entity):
            entity_cfg = entity_by_name[entity_name]
            route_path = self._route_path(entity_name, path_by_entity)
            # The route that exposes this entity owns its controller; an
            # entity with no route (possible for `resource` style) keeps it.
            controller_owner = route_owner_by_entity.get(entity_name) or owner(
                entity_cfg
            )
            if style_by_entity.get(entity_name) == "resource":
                # ResourceGenerator writes output_dir/controllers/*.py
                with generating(
                    "resource", controller_owner, subdirectory_of=True
                ) as staged_dir:
                    load_generator(
                        "resource", output_dir=staged_dir
                    ).generate(
                        entity_name,
                        fields_str=_fields_str(entity_cfg),
                        force=True,
                    )
            else:
                with generating("controller", controller_owner) as staged_dir:
                    load_generator(
                        "controller", output_dir=staged_dir
                    ).generate(
                        entity_name,
                        fields_str=_fields_str(entity_cfg),
                        path=route_path,
                        force=True,
                    )

        # Stage → destination mapping and per-file reconciliation are entirely
        # data-driven from VERB_SPECS (see gen/node_generators.py). Adding a
        # generator-backed node adds a registry entry rather than another
        # branch here.
        # The controller's audit hook imports the audit repository, which
        # lives in the entity's own context under modular -- so the import
        # root is the entity's, not the global one (which does not exist).
        audit_repo_roots = {
            entity_name: place.imports(entity_cfg_by_name.get(entity_name))[
                "repositories"
            ]
            for entity_name in audit_entities_sorted
        }
        reconcile_ctx = ReconcileContext(
            layout=self._layout,
            entity_by_stem={entity.name: entity for entity in entities},
            channel_by_stem={c.name: c for c in enabled_channels},
            event_handler_by_stem={
                f"{snake_case(h.name)}_handler": h for h in resolved_handlers
            },
            projection_by_stem={
                f"{snake_case(p.name)}_projection": p
                for p in resolve_projections(
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
                        f"{audit_repo_roots[entity_name]}."
                        f"{entity_name}_audit_repository"
                    ),
                )
                for entity_name in audit_entities_sorted
            },
        )
        # Committing staged files is `gen/modular`'s job: which verb
        # produced a file, which context owns it, and which import roots its
        # reconcilers must name are one decision, taken in one place.
        commit_staged(
            staging.staged(),
            files=files,
            ledger=ledger,
            reconcile_ctx=reconcile_ctx,
        )
        shutil.rmtree(staging_root, ignore_errors=True)

        # HTTP smoke tests only for entities that actually have routes.
        routed_names = set(ops_by_entity)
        for entity in entities:
            if entity.name in routed_names:
                rel = crud_test_filename(entity)
                ledger.record(rel, node_id=owner(entity))
                files[rel] = emit_crud_test(
                    entity,
                    ops=frozenset(ops_by_entity[entity.name]),
                    path=self._route_path(entity.name, path_by_entity),
                    mods=mods,
                )

        # ── modular: bounded contexts, their wiring, the composition root ──
        #
        # Emitted last so it can see everything the rest of the run
        # produced, and kept in one place rather than threaded through every
        # emitter: the modular-only artifacts are exactly the files that
        # have no counterpart under minimal or structured.
        if has_modules:
            emit_modular_project(graph, files, ledger, layout=self._layout)

        app_prefix = f"{app_name}/"
        prune_stale_generated(
            Path(self.output_dir) / app_name,
            keep={f"{app_prefix}{rel}" for rel in files},
            layout=self._layout,
        )

        staged_paths = sorted(files)
        total = len(staged_paths)
        for index, rel_path in enumerate(staged_paths, start=1):
            self.stage(app_prefix + rel_path, files[rel_path])
            if on_file is not None:
                # Attribution from the ledger; matching paths would re-copy layout.
                on_file(rel_path, index, total, ledger.record_for(rel_path))

        result = self.commit(GenerationOptions(policy=CollisionPolicy.OVERWRITE))
        if self._post_process:
            format_project(Path(self.output_dir) / app_name)
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

    def _monorepo_root(self) -> str:
        """Path prefix for generated [tool.uv.sources]."""
        return self._framework_root or FRAMEWORK_REPO_REL


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
