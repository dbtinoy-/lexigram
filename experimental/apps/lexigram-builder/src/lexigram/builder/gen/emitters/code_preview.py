"""In-memory code preview emitter for the frontend code tab.

Generates lexigram-flavored code snippets without writing to disk.
"""

from __future__ import annotations

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
from lexigram.builder.gen.emitters.audit_postprocess import (
    ControllerAuditHooks,
    apply_audit,
)
from lexigram.builder.gen.emitters.auth_policy_emitter import emit_auth_policy_module
from lexigram.builder.gen.emitters.context import (
    pascal_entity,
    snake_case,
    table_name,
)
from lexigram.builder.gen.emitters.contract_postprocess import (
    ContractBinding,
    ControllerContract,
    apply_contract,
    emit_contract_module,
)
from lexigram.builder.gen.emitters.dataloader_emitter import emit_dataloader_module
from lexigram.builder.gen.emitters.email_emitter import (
    emit_email_module,
    emit_emails_init,
    emit_mailer_helper,
)
from lexigram.builder.gen.emitters.file_upload_emitter import (
    emit_upload_controller,
    emit_upload_storage,
)
from lexigram.builder.gen.emitters.flag_postprocess import (
    ControllerFlagGates,
    apply_flag_gates,
)
from lexigram.builder.gen.emitters.guard_postprocess import (
    ControllerGuards,
    apply_guards,
    emit_rate_limit_middleware,
    emit_rate_limit_module,
)
from lexigram.builder.gen.emitters.http_client_emitter import emit_api_client_module
from lexigram.builder.gen.emitters.interceptor_emitter import emit_interceptor_module
from lexigram.builder.gen.emitters.saga_emitter import emit_saga_module
from lexigram.builder.gen.emitters.scaffold import emit_scaffold_files
from lexigram.builder.gen.emitters.search_emitter import (
    effective_engine,
    emit_search_controller,
    emit_search_migration,
    emit_search_repository,
)
from lexigram.builder.gen.emitters.storage_driver_emitter import (
    emit_storage_driver_module,
)
from lexigram.builder.gen.emitters.validator_emitter import (
    emit_validator_module,
)
from lexigram.builder.graph.models import (
    ApiClientConfig,
    ApiKeyGroupConfig,
    AppSettingsConfig,
    AuditLogConfig,
    AuthConfig,
    AuthPolicyConfig,
    ContractConfig,
    DataLoaderConfig,
    EmailTemplateConfig,
    EntityConfig,
    FeatureFlagConfig,
    FileUploadConfig,
    GraphDocument,
    GraphNode,
    InterceptorConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
    SagaConfig,
    SearchIndexConfig,
    StorageDriverConfig,
    ValidatorConfig,
)


def emit_code_preview(document: GraphDocument) -> list[dict[str, str]]:
    """Generate preview files from a graph document.

    Returns a list of {path, language, content} dicts for the frontend code tab.
    """
    settings_node = None
    for node in document.nodes:
        if node.kind == "app_settings" and isinstance(node.config, AppSettingsConfig):
            settings_node = node
            break

    if settings_node is None:
        return []

    cfg = settings_node.config
    assert isinstance(cfg, AppSettingsConfig)
    app_name = cfg.app_name

    entities: list[EntityConfig] = []
    for node in document.nodes:
        if node.kind == "entity" and isinstance(node.config, EntityConfig):
            entities.append(node.config)

    flags: list[FeatureFlagConfig] = []
    for node in document.nodes:
        if node.kind == "feature_flag" and isinstance(
            node.config, FeatureFlagConfig
        ):
            flags.append(node.config)
    flags.sort(key=lambda f: f.name)
    enabled_flags = [f for f in flags if f.enabled]

    api_clients: list[ApiClientConfig] = []
    for node in document.nodes:
        if node.kind == "api_client" and isinstance(node.config, ApiClientConfig):
            api_clients.append(node.config)
    api_clients.sort(key=lambda c: c.name)
    enabled_api_clients = [c for c in api_clients if c.enabled]

    sagas: list[SagaConfig] = []
    for node in document.nodes:
        if node.kind == "saga" and isinstance(node.config, SagaConfig):
            sagas.append(node.config)
    sagas.sort(key=lambda s: s.name)
    enabled_sagas = [s for s in sagas if s.enabled]

    interceptors: list[InterceptorConfig] = []
    for node in document.nodes:
        if node.kind == "interceptor" and isinstance(node.config, InterceptorConfig):
            interceptors.append(node.config)
    interceptors.sort(key=lambda s: s.name)
    enabled_interceptors = [s for s in interceptors if s.enabled]

    dataloaders: list[DataLoaderConfig] = []
    for node in document.nodes:
        if node.kind == "dataloader" and isinstance(node.config, DataLoaderConfig):
            dataloaders.append(node.config)
    dataloaders.sort(key=lambda s: s.name)
    enabled_dataloaders = [s for s in dataloaders if s.enabled]

    auth_policies: list[AuthPolicyConfig] = []
    for node in document.nodes:
        if node.kind == "auth_policy" and isinstance(node.config, AuthPolicyConfig):
            auth_policies.append(node.config)
    auth_policies.sort(key=lambda s: s.name)
    enabled_auth_policies = [s for s in auth_policies if s.enabled]

    storage_drivers: list[StorageDriverConfig] = []
    for node in document.nodes:
        if node.kind == "storage_driver" and isinstance(
            node.config, StorageDriverConfig
        ):
            storage_drivers.append(node.config)
    storage_drivers.sort(key=lambda c: c.name)
    enabled_storage_drivers = [c for c in storage_drivers if c.enabled]


    route_bindings: list[tuple[RouteConfig, EntityConfig]] = []
    by_id: dict[str, GraphNode] = {n.id: n for n in document.nodes}
    for node in document.nodes:
        if node.kind == "route" and isinstance(node.config, RouteConfig):
            for edge in document.edges:
                if edge.src == node.id:
                    target = by_id.get(edge.dst)
                    if target and isinstance(target.config, EntityConfig):
                        route_bindings.append((node.config, target.config))
                        break

    # Guard-chain wiring (Workstream B): routes guarded by auth/role nodes
    # decorate their entity's controller handlers; rate_limit nodes emit
    # definition-only policy modules.
    guard_auth_ops_by_entity: dict[str, set[str]] = {}
    guard_roles_by_entity: dict[str, dict[str, set[str]]] = {}
    # Contract bindings per served entity (op -> binding), mirrors writer.
    contract_bindings_by_entity: dict[str, dict[str, ContractBinding]] = {}
    # Flag gates per served entity (flag key -> ops), mirrors writer.
    flag_gates_by_entity: dict[str, dict[str, set[str]]] = {}
    validators: list[ValidatorConfig] = []
    search_indexes: list[SearchIndexConfig] = []
    file_uploads: list[FileUploadConfig] = []
    contracts: list[ContractConfig] = []
    auths: list[AuthConfig] = []
    roles: list[RoleConfig] = []
    rate_limits: list[RateLimitConfig] = []
    for node in document.nodes:
        if isinstance(node.config, AuthConfig):
            auths.append(node.config)
        elif isinstance(node.config, RoleConfig):
            roles.append(node.config)
        elif isinstance(node.config, RateLimitConfig):
            rate_limits.append(node.config)
        elif isinstance(node.config, ContractConfig):
            contracts.append(node.config)
        elif isinstance(node.config, ValidatorConfig) and node.kind == "validator":
            validators.append(node.config)
        elif isinstance(node.config, SearchIndexConfig) and (
            node.kind == "search_index"
        ):
            search_indexes.append(node.config)
        elif isinstance(node.config, FileUploadConfig) and (
            node.kind == "file_upload"
        ):
            file_uploads.append(node.config)
    paths_by_rate_limit: dict[str, set[str]] = {}
    for node in document.nodes:
        if node.kind != "route" or not isinstance(node.config, RouteConfig):
            continue
        route_cfg = node.config
        # The entity this route serves (guard edges may precede it).
        entity_name = next(
            (
                target.config.name
                for edge in document.edges
                if edge.src == node.id
                and (target := by_id.get(edge.dst)) is not None
                and isinstance(target.config, EntityConfig)
            ),
            None,
        )
        if entity_name is None:
            continue
        for edge in document.edges:
            if edge.src != node.id:
                continue
            dst = by_id.get(edge.dst)
            if dst is None:
                continue
            if isinstance(dst.config, AuthConfig):
                guard_auth_ops_by_entity.setdefault(entity_name, set()).update(
                    route_cfg.ops
                )
            elif isinstance(dst.config, RoleConfig):
                op_roles = guard_roles_by_entity.setdefault(entity_name, {})
                for op in route_cfg.ops:
                    op_roles.setdefault(op, set()).add(dst.config.name)
            elif isinstance(dst.config, RateLimitConfig) and route_cfg.path_prefix:
                paths_by_rate_limit.setdefault(dst.config.name, set()).add(
                    route_cfg.path_prefix
                )
            elif isinstance(dst.config, ContractConfig) and dst.config.enabled:
                op_bindings = contract_bindings_by_entity.setdefault(
                    entity_name, {}
                )
                for op in route_cfg.ops:
                    op_bindings.setdefault(
                        op, ContractBinding(contract=dst.config)
                    )
            elif (
                isinstance(dst.config, FeatureFlagConfig)
                and dst.config.enabled
            ):
                flag_gates_by_entity.setdefault(entity_name, {}).setdefault(
                    dst.config.name, set()
                ).update(route_cfg.ops)

    # Search-index wiring (nodes plan N3.2): merge (entity -> search_index)
    # edges per entity, mirroring the writer (enabled only, first engine
    # wins, fields deduped in order, boost dicts merged).
    search_cfg_by_entity: dict[str, SearchIndexConfig] = {}
    for edge in document.edges:
        src_node = by_id.get(edge.src)
        dst_node = by_id.get(edge.dst)
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

    # Audit-log wiring (nodes plan N4.1): merge (entity -> audit_log)
    # edges per entity, mirroring the writer (enabled only, op union).
    audit_cfg_by_entity: dict[str, AuditLogConfig] = {}
    for edge in document.edges:
        src_node = by_id.get(edge.src)
        dst_node = by_id.get(edge.dst)
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

    # API-key group wiring (nodes plan N4.2): screen-managed kind — the
    # first enabled group defines header/prefix; scopes union across all.
    api_key_groups: list[ApiKeyGroupConfig] = [
        n.config
        for n in document.nodes
        if n.kind == "api_key_group"
        and isinstance(n.config, ApiKeyGroupConfig)
    ]
    api_key_groups.sort(key=lambda g: g.name)
    enabled_api_key_groups = [g for g in api_key_groups if g.enabled]

    # Email template wiring (nodes plan N4.3): screen-managed kind — one
    # Mailable module per enabled template + shared mailer/init modules.
    email_templates: list[EmailTemplateConfig] = [
        n.config
        for n in document.nodes
        if n.kind == "email_template"
        and isinstance(n.config, EmailTemplateConfig)
    ]
    email_templates.sort(key=lambda t: t.name)
    enabled_email_templates = [t for t in email_templates if t.enabled]

    # File-upload wiring (nodes plan N3.3): route-attached merge,
    # mirroring the writer (first enabled binding per route wins).
    upload_cfg_by_route: dict[str, FileUploadConfig] = {}
    if any(fu.enabled for fu in file_uploads):
        for edge in document.edges:
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
    upload_entities: dict[str, FileUploadConfig] = {}
    upload_route_paths: dict[str, str] = {}
    for route_id, upload_cfg in upload_cfg_by_route.items():
        up_route_node = by_id[route_id]
        up_route_cfg = up_route_node.config
        assert isinstance(up_route_cfg, RouteConfig)
        entity_name = ""
        for edge in document.edges:
            if edge.src != route_id:
                continue
            target = by_id.get(edge.dst)
            if target and isinstance(target.config, EntityConfig):
                entity_name = target.config.name
                break
        if entity_name:
            route_path = _search_route_path(entity_name, route_bindings)
        else:
            prefix = (up_route_cfg.path_prefix or "").strip()
            if not prefix:
                continue
            route_path = "/" + prefix.strip("/")
        if entity_name in upload_entities:
            continue
        upload_entities[entity_name] = upload_cfg
        upload_route_paths[entity_name] = route_path

    # Get scaffold files from the real codegen
    field_types = {f.type for ent in entities for f in ent.fields}
    extra_deps: tuple[str, ...] = (
        ("email-validator>=2.0.0",) if "email" in field_types else ()
    ) + (("python-multipart>=0.0.9",) if file_uploads else ())
    scaffold = emit_scaffold_files(
        app_name,
        entities,
        route_bindings,
        relative_root="../../lexigram",
        structure=cfg.structure,
        extra_dependencies=extra_deps,
        api_clients=bool(enabled_api_clients),
        storage_drivers=bool(enabled_storage_drivers),
        sagas=tuple(enabled_sagas),
        flags=tuple(enabled_flags),
        auths=tuple(auths),
        api_key_groups=tuple(enabled_api_key_groups),
        email_templates=tuple(enabled_email_templates),
        roles=tuple(roles),
        policies=tuple(rate_limits),
        search_entities=tuple(sorted(search_cfg_by_entity)),
        audit_repositories=tuple(sorted(audit_cfg_by_entity)),
        upload_controllers=tuple(
            (name, cfg.name) for name, cfg in sorted(upload_entities.items())
        ),
    )

    files: list[dict[str, str]] = []
    _LANG_MAP = {
        "py": "python", "toml": "toml", "yaml": "yaml",
        "md": "markdown", "ini": "ini", "mako": "text",
    }

    for path, content in scaffold.items():
        ext = path.rsplit(".", 1)[-1] if "." in path else ""
        files.append({
            "path": path,
            "language": _LANG_MAP.get(ext, "text"),
            "content": content,
        })

    # Add controller previews for routed entities
    seen: set[str] = set()
    for route_cfg, entity_cfg in route_bindings:
        if entity_cfg.name in seen:
            continue
        seen.add(entity_cfg.name)
        content = _controller_preview(
            entity_cfg,
            route_cfg,
            with_flags=entity_cfg.name in flag_gates_by_entity,
        )
        # Contract wiring first (payload/response swaps), then flag gates,
        # then guards — mirrors the writer's _reconcile_controller order.
        wiring = contract_bindings_by_entity.get(entity_cfg.name)
        if wiring is not None:
            content = apply_contract(
                content, ControllerContract(by_op=dict(wiring))
            )
        gates = flag_gates_by_entity.get(entity_cfg.name)
        if gates is not None:
            content = apply_flag_gates(
                content,
                ControllerFlagGates(
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
                ),
            )
        guards = ControllerGuards(
            ops=frozenset(
                guard_auth_ops_by_entity.get(entity_cfg.name, set())
                - set(guard_roles_by_entity.get(entity_cfg.name, {}))
            ),
            roles_by_op={
                op: tuple(sorted(role_names))
                for op, role_names in guard_roles_by_entity.get(
                    entity_cfg.name, {}
                ).items()
            },
        )
        content = apply_guards(content, guards)
        audit = audit_cfg_by_entity.get(entity_cfg.name)
        if audit is not None and audit.operations:
            content = apply_audit(
                content,
                ControllerAuditHooks(
                    ops=frozenset(audit.operations),
                    repo_class=f"{pascal_entity(entity_cfg.name)}AuditRepository",
                    repo_module=(
                        "app.repositories."
                        f"{snake_case(entity_cfg.name)}_audit_repository"
                    ),
                ),
            )
        files.append({
            "path": f"src/app/controllers/{snake_case(entity_cfg.name)}_controller.py",
            "language": "python",
            "content": content,
        })

    # Add feature-flag definition previews (mirrors the writer's staged
    # output of the lexigram-features `feature_flag` generator).
    for flag in enabled_flags:
        files.append({
            "path": f"src/app/features/{snake_case(flag.name)}_flag.py",
            "language": "python",
            "content": _flag_preview(flag),
        })

    # Guard scaffolds (mirrors the writer's staged lexigram-auth output).
    for auth in sorted(auths, key=lambda a: a.name):
        files.append({
            "path": f"src/app/guards/{snake_case(auth.name)}_auth_guard.py",
            "language": "python",
            "content": _auth_guard_preview(auth),
        })
    for role in sorted(roles, key=lambda r: r.name):
        files.append({
            "path": f"src/app/guards/{snake_case(role.name)}_guard.py",
            "language": "python",
            "content": _role_guard_preview(role),
        })
    for limit in sorted(rate_limits, key=lambda r: r.name):
        wired = tuple(sorted(paths_by_rate_limit.get(limit.name, set())))
        files.append({
            "path": f"src/app/policies/{snake_case(limit.name)}_rate_limit.py",
            "language": "python",
            "content": emit_rate_limit_module(limit, paths=wired, doc=limit.description),
        })

    # Rate-limit enforcement middleware (mirrors the writer's emission).
    if rate_limits:
        files.append({
            "path": "src/app/middleware/rate_limit.py",
            "language": "python",
            "content": emit_rate_limit_middleware(
                [
                    (limit, tuple(sorted(paths_by_rate_limit.get(limit.name, set()))))
                    for limit in sorted(rate_limits, key=lambda r: r.name)
                ]
            ),
        })

    # Contract DTO modules (mirrors the writer's builder-side emission).
    for contract in sorted(
        (c for c in contracts if c.enabled), key=lambda c: c.name
    ):
        files.append({
            "path": f"src/app/contracts/{contract.name}.py",
            "language": "python",
            "content": emit_contract_module(contract),
        })

    # Validator constraint modules (mirrors the writer's emission — nodes
    # plan N3.1): merge (entity -> validator) edges per entity.
    validator_cfg_by_name = {
        v.name: v for v in validators if v.enabled
    }
    validator_rules_by_entity: dict[str, list[tuple[str, str]]] = {}
    for edge in document.edges:
        src_node = by_id.get(edge.src)
        dst_node = by_id.get(edge.dst)
        if (
            src_node is None
            or dst_node is None
            or not isinstance(src_node.config, EntityConfig)
            or not isinstance(dst_node.config, ValidatorConfig)
            or dst_node.config.name not in validator_cfg_by_name
        ):
            continue
        validator_rules_by_entity.setdefault(
            src_node.config.name, []
        ).extend(validator_cfg_by_name[dst_node.config.name].rules)
    for entity_name in sorted(validator_rules_by_entity):
        rules = tuple(validator_rules_by_entity[entity_name])
        if not rules:
            continue
        merged = ValidatorConfig(name=f"validate_{entity_name}", rules=rules)
        files.append({
            "path": f"src/app/validators/{entity_name}.py",
            "language": "python",
            "content": emit_validator_module(entity_name, merged),
        })
        files.append({
            "path": "src/app/validators/__init__.py",
            "language": "python",
            "content": "# generated by lexigram-builder - do not edit\n",
        })
        break  # one __init__.py entry suffices

    # Search-index artifacts (mirrors the writer's emission — nodes plan
    # N3.2): FTS migration (chained onto the entity-migration head),
    # repository and controller per wired entity.
    search_entities_sorted = sorted(search_cfg_by_entity)
    search_prev_rev: str | None = f"{len(entities):03d}" if entities else None
    for idx, entity_name in enumerate(search_entities_sorted):
        search_cfg = search_cfg_by_entity[entity_name]
        route_path = _search_route_path(entity_name, route_bindings)
        if effective_engine(search_cfg) == "fts":
            revision = f"b{idx + 1:04d}_{entity_name}_search_fts"
            files.append({
                "path": f"migrations/versions/{revision}.py",
                "language": "python",
                "content": emit_search_migration(
                    entity_name,
                    search_cfg,
                    revision=revision,
                    prev_revision=search_prev_rev,
                ),
            })
            search_prev_rev = revision
        files.append({
            "path": f"src/app/repositories/{entity_name}_search_repository.py",
            "language": "python",
            "content": emit_search_repository(entity_name, search_cfg),
        })
        files.append({
            "path": f"src/app/controllers/{entity_name}_search_controller.py",
            "language": "python",
            "content": emit_search_controller(entity_name, route_path),
        })

    # Audit-log artifacts (mirrors the writer's emission — nodes plan
    # N4.1): audit-table migration (chained onto the search head) and
    # repository per wired entity.
    audit_prev_rev = search_prev_rev
    for idx, entity_name in enumerate(sorted(audit_cfg_by_entity)):
        audit_cfg = audit_cfg_by_entity[entity_name]
        revision = f"b{idx + 1:04d}_{entity_name}_audit_log"
        files.append({
            "path": f"migrations/versions/{revision}.py",
            "language": "python",
            "content": emit_audit_migration(
                entity_name,
                audit_cfg,
                revision=revision,
                prev_revision=audit_prev_rev,
            ),
        })
        audit_prev_rev = revision
        files.append({
            "path": f"src/app/repositories/{entity_name}_audit_repository.py",
            "language": "python",
            "content": emit_audit_repository(entity_name, audit_cfg),
        })

    # API-key artifacts (mirrors the writer's emission — nodes plan
    # N4.2): migration chained onto the audit head + repository + auth
    # constants module for the first enabled group.
    if enabled_api_key_groups:
        revision = "b0001_api_keys"
        files.append({
            "path": f"migrations/versions/{revision}.py",
            "language": "python",
            "content": emit_api_keys_migration(
                revision=revision,
                prev_revision=audit_prev_rev,
            ),
        })
        files.append({
            "path": "src/app/repositories/api_key_repository.py",
            "language": "python",
            "content": emit_api_key_repository(),
        })
        files.append({
            "path": "src/app/auth/__init__.py",
            "language": "python",
            "content": "# generated by lexigram-builder - do not edit\n",
        })
        files.append({
            "path": "src/app/auth/api_keys.py",
            "language": "python",
            "content": emit_api_keys_auth_module(
                enabled_api_key_groups[0],
                merged_api_key_scopes(enabled_api_key_groups),
            ),
        })

    # Email artifacts (mirrors the writer's emission — nodes plan N4.3):
    # one Mailable module per enabled template + shared mailer/init.
    if enabled_email_templates:
        files.append({
            "path": "src/app/emails/__init__.py",
            "language": "python",
            "content": emit_emails_init(enabled_email_templates),
        })
        files.append({
            "path": "src/app/emails/mailer.py",
            "language": "python",
            "content": emit_mailer_helper(),
        })
        for template in enabled_email_templates:
            files.append({
                "path": f"src/app/emails/{template.name}.py",
                "language": "python",
                "content": emit_email_module(template),
            })

    # File-upload artifacts (mirrors the writer's emission — nodes
    # plan N3.3): storage service + upload controller per wired route.
    for entity_name, upload_cfg in sorted(upload_entities.items()):
        route_path = upload_route_paths[entity_name]
        files.append({
            "path": f"src/app/uploads/{upload_cfg.name}_upload_storage.py",
            "language": "python",
            "content": emit_upload_storage(entity_name, upload_cfg),
        })
        files.append({
            "path": (
                f"src/app/controllers/{upload_cfg.name}_upload_controller.py"
            ),
            "language": "python",
            "content": emit_upload_controller(
                entity_name, route_path, upload_cfg
            ),
        })
    if upload_entities:
        files.append({
            "path": "src/app/uploads/__init__.py",
            "language": "python",
            "content": (
                "# Generated by lexigram-builder. Do not edit; regenerate"
                " instead.\n"
            ),
        })


    for saga in enabled_sagas:
        files.append({
            "path": f"src/app/sagas/{snake_case(saga.name)}_saga.py",
            "language": "python",
            "content": emit_saga_module(saga),
        })
    for interceptor in enabled_interceptors:
        files.append({
            "path": (
                f"src/app/interceptors/{snake_case(interceptor.name)}_interceptor.py"
            ),
            "language": "python",
            "content": emit_interceptor_module(interceptor),
        })
    for loader in enabled_dataloaders:
        files.append(
            {
                "path": (
                    f"src/app/graphql/dataloaders/{snake_case(loader.name)}.py"
                ),
                "language": "python",
                "content": emit_dataloader_module(loader),
            }
        )

    for policy in enabled_auth_policies:
        files.append(
            {
                "path": (
                    f"src/app/policies/{snake_case(policy.name)}_policy.py"
                ),
                "language": "python",
                "content": emit_auth_policy_module(policy),
            }
        )

    for client in enabled_api_clients:
        files.append({
            "path": f"src/app/clients/{snake_case(client.name)}_client.py",
            "language": "python",
            "content": emit_api_client_module(client),
        })
    for driver in enabled_storage_drivers:
        files.append({
            "path": f"src/app/storage/backends/{snake_case(driver.name)}.py",
            "language": "python",
            "content": emit_storage_driver_module(driver),
        })

    return files


def _search_route_path(
    entity_name: str,
    route_bindings: list[tuple[RouteConfig, EntityConfig]],
) -> str:
    """Resolve the API base path for a search controller.

    Mirrors ``ProjectWriter._route_path``: prefer an explicit route
    ``path_prefix`` from the canvas; otherwise the pluralized table name.
    """
    for route_cfg, ent in route_bindings:
        if ent.name == entity_name and route_cfg.path_prefix:
            return "/" + route_cfg.path_prefix.strip("/")
    return f"/{table_name(entity_name)}"


def _flag_preview(flag: FeatureFlagConfig) -> str:
    pascal = pascal_entity(flag.name)
    key = snake_case(flag.name)
    description = flag.description or f"Toggle for the {pascal} feature"
    return (
        "# generated by lexigram-builder - do not edit\n"
        '"""Feature flag definition.\n'
        "\n"
        "Generated scaffold — declare the flag key and default rollout here so\n"
        "the rest of the application imports one canonical definition.\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "from dataclasses import dataclass\n"
        "\n"
        "\n"
        "@dataclass(frozen=True, slots=True)\n"
        f"class {pascal}Flag:\n"
        f'    """Definition of the ``{key}`` feature flag."""\n'
        "\n"
        f'    key = "{key}"\n'
        f'    description = "{description}"\n'
        "    default_enabled = False\n"
        "\n"
        "    @classmethod\n"
        "    def is_enabled(cls, context: dict[str, object] | None = None) -> bool:\n"
        '        """Return whether the flag is enabled for *context*."""\n'
        "        # TODO: consult your FlagManager / provider here.\n"
        "        return cls.default_enabled\n"
    )


def _controller_preview(
    entity: EntityConfig, route: RouteConfig, *, with_flags: bool = False
) -> str:
    pascal = pascal_entity(entity.name)
    table = snake_case(entity.name)
    ops = route.ops or ("create", "get", "list", "update", "delete")

    imports = [
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "",
        "from pydantic import ValidationError",
        "from starlette.requests import Request",
        "from lexigram.web import Controller, post, get, put, delete",
        "from lexigram.web.exceptions import BadRequestError, NotFoundError",
        f"from app.exceptions import {pascal}NotFoundError",
        f"from app.models.{table} import {pascal}Create, {pascal}Update",
        f"from app.repositories.{table}_repository import {pascal}Repository",
    ]
    if with_flags:
        imports.append("from lexigram.features import FlagManager")

    methods = []
    for op in ops:
        if op == "create":
            methods.append(
                f"    async def create(self, request: Request) -> dict[str, Any]:\n"
                f'        """Create a new {pascal}."""\n'
                f"        data = await _read_body(request)\n"
                f"        try:\n"
                f"            payload = {pascal}Create(**data)\n"
                f"        except ValidationError as exc:\n"
                f"            raise BadRequestError(\n"
                f'                f"Invalid {pascal} payload: {{exc}}"\n'
                f"            ) from exc\n"
                f'        created = await self.repo.create(payload.model_dump(mode="json"))\n'
                f"        return _to_dict(created)"
            )
        elif op == "get":
            methods.append(
                f"    async def get(self, item_id: str) -> dict[str, Any]:\n"
                f'        """Get {pascal} by ID."""\n'
                f"        item = await self.repo.get(item_id)\n"
                f"        if item is None:\n"
                f"            raise {pascal}NotFoundError(item_id)\n"
                f"        return _to_dict(item)"
            )
        elif op == "list":
            methods.append(
                f"    async def list(\n"
                f"        self,\n"
                f"        limit: int = 20,\n"
                f"    ) -> dict[str, Any]:\n"
                f'        """List all {pascal} records."""\n'
                f"        items = await self.repo.list(limit=limit)\n"
                f"        return {{\n"
                f'            "items": [_to_dict(item) for item in items],\n'
                f"        }}"
            )
        elif op == "update":
            methods.append(
                f"    async def update(self, item_id: str, request: Request) -> dict[str, Any]:\n"
                f'        """Update {pascal} by ID."""\n'
                f"        data = await _read_body(request)\n"
                f"        try:\n"
                f"            payload = {pascal}Update(**data)\n"
                f"        except ValidationError as exc:\n"
                f"            raise BadRequestError(\n"
                f'                f"Invalid {pascal} payload: {{exc}}"\n'
                f"            ) from exc\n"
                f"        updated = await self.repo.update(\n"
                f"            item_id, payload.model_dump(exclude_unset=True)\n"
                f"        )\n"
                f"        return _to_dict(updated)"
            )
        elif op == "delete":
            methods.append(
                f"    async def delete(self, item_id: str) -> None:\n"
                f'        """Delete {pascal} by ID."""\n'
                f"        deleted = await self.repo.delete(item_id)\n"
                f"        if not deleted:\n"
                f"            raise {pascal}NotFoundError(item_id)"
            )

    methods_str = "\n\n".join(methods) if methods else "    pass"
    imports_str = "\n".join(imports)
    path = (route.path_prefix or "").strip() or f"/{table}"

    # Module helpers mirroring the framework controller template's shape
    # (serialization + JSON body parsing), so previewed handlers read the
    # same as written ones.
    helpers = (
        "\n\ndef _to_dict(item: Any) -> dict[str, Any]:\n"
        '    """Serialize a repo result to a JSON-safe dict."""\n'
        "    if isinstance(item, dict):\n"
        "        return item\n"
        '    if hasattr(item, "to_dict"):\n'
        "        return item.to_dict()\n"
        '    return {"value": item}\n'
        "\n"
        "\n"
        "async def _read_body(request: Request) -> dict[str, Any]:\n"
        '    """Parse and shallow-validate the JSON request body."""\n'
        "    try:\n"
        "        data: Any = await request.json()\n"
        "    except Exception as exc:\n"
        '        raise BadRequestError("Invalid JSON body") from exc\n'
        "    if not isinstance(data, dict) or not data:\n"
        '        raise BadRequestError("Request body must be a non-empty JSON object")\n'
        "    return data\n"
    )

    return (
        "# generated by lexigram-builder - do not edit\n"
        f"{imports_str}\n"
        "\n"
        "\n"
        f"class {pascal}Controller(Controller):\n"
        f'    """CRUD controller for {pascal}."""\n'
        "\n"
        f'    path = "{path}"\n'
        f'    tags = ["{pascal}"]\n'
        "\n"
        + (
            "    def __init__(\n"
            f"        self, repo: {pascal}Repository, flags: FlagManager\n"
            "    ) -> None:\n"
            "        super().__init__()\n"
            "        self.repo = repo\n"
            "        self._flags = flags\n"
            "\n"
            if with_flags
            else ""
        )
        + f"{methods_str}\n"
        f"{helpers}"
    )


def _auth_guard_preview(auth: AuthConfig) -> str:
    pascal = pascal_entity(auth.name)
    key = snake_case(auth.name)
    return (
        "# generated by lexigram-builder - do not edit\n"
        f'"""{pascal} authentication guard.\n'
        "\n"
        "Generated scaffold — implement the credential check below.\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "from typing import Any\n"
        "\n"
        "\n"
        f"class {pascal}AuthGuard:\n"
        f'    """Authenticate requests using the {key} scheme."""\n'
        "\n"
        f'    scheme = "{key}"\n'
        "\n"
        '    def __init__(self, credentials_header: str = "Authorization") -> None:\n'
        "        self.credentials_header = credentials_header\n"
        "\n"
        "    async def authenticate(self, request: Any) -> Any | None:\n"
        '        """Authenticate the request and return the principal."""\n'
        "        # TODO: verify credentials against your identity provider.\n"
        "        return None\n"
    )


def _role_guard_preview(role: RoleConfig) -> str:
    pascal = pascal_entity(role.name)
    key = snake_case(role.name)
    permissions = ", ".join(role.permissions) or "none"
    inherits = ", ".join(role.inherits) or "none"
    return (
        "# generated by lexigram-builder - do not edit\n"
        f'"""{pascal} authorization guard (role variant).\n'
        "\n"
        f"Permissions: {permissions}.\n"
        f"Inherits: {inherits}.\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "from lexigram.auth.web.guards import RoleGuard\n"
        "\n"
        "\n"
        f"class {pascal}RoleGuard(RoleGuard):\n"
        f'    """Role-based guard requiring the ``{key}`` role."""\n'
        "\n"
        "    def __init__(self) -> None:\n"
        f'        super().__init__("{key}")\n'
    )
