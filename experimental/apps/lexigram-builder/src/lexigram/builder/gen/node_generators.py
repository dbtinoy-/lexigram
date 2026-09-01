"""Declarative registry for framework-CLI generator-backed canvas nodes.

Each drawable node kind that produces files through a framework ``lexigram``
CLI generator (discovered via :mod:`lexigram.builder.gen.cli_bridge`) is
described by a :class:`VerbSpec`. The spec captures everything the
:class:`~lexigram.builder.gen.writer.ProjectWriter` needs to stage, generate
into, place, and post-process that generator's output — so adding a new
generator-backed node is a single registry entry rather than another branch
in a growing if/else chain.

Two registries are provided:

* :data:`VERB_SPECS` — keyed by framework generator *verb* (e.g. ``service``,
  ``exception_filter``). Drives staging-dir creation, destination mapping, and
  per-file reconciliation.
* :data:`ENTITY_ATTACHED_VERBS` — the verbs that are driven by an
  ``entity -> <node>`` edge and take the entity's ``fields_str``; the writer
  collects their targets uniformly from edges.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lexigram.contracts.cli.generators import pascal_case

from lexigram.builder.gen.emitters.audit_postprocess import (
    ControllerAuditHooks,
    apply_audit,
)
from lexigram.builder.gen.emitters.channel_postprocess import reconcile_channel
from lexigram.builder.gen.emitters.contract_postprocess import (
    ControllerContract,
    apply_contract,
)
from lexigram.builder.gen.emitters.controller_postprocess import reconcile_controller
from lexigram.builder.gen.emitters.error_postprocess import reconcile_error
from lexigram.builder.gen.emitters.event_postprocess import reconcile_event
from lexigram.builder.gen.emitters.filter_postprocess import (
    reconcile_exception_filter,
)
from lexigram.builder.gen.emitters.flag_postprocess import (
    ControllerFlagGates,
    apply_flag_gates,
)
from lexigram.builder.gen.emitters.graphql_postprocess import reconcile_graphql
from lexigram.builder.gen.emitters.guard_postprocess import (
    ControllerGuards,
    apply_guards,
    reconcile_guard,
)
from lexigram.builder.gen.emitters.handler_postprocess import (
    reconcile_event_handler,
)
from lexigram.builder.gen.emitters.health_postprocess import reconcile_health
from lexigram.builder.gen.emitters.model_postprocess import reconcile_model
from lexigram.builder.gen.emitters.projection_postprocess import (
    reconcile_projection,
)
from lexigram.builder.gen.emitters.seeder_postprocess import reconcile_seeder
from lexigram.builder.gen.emitters.task_postprocess import reconcile_task
from lexigram.builder.gen.emitters.webhook_postprocess import reconcile_webhook
from lexigram.builder.graph.models import (
    ChannelConfig,
    EntityConfig,
    EventHandlerConfig,
    ProjectionConfig,
)


@dataclass(frozen=True, slots=True)
class ReconcileContext:
    """Per-project context reconcilers may need to rewrite a file."""

    entity_by_stem: dict[str, EntityConfig]
    channel_by_stem: dict[str, ChannelConfig]
    event_handler_by_stem: dict[str, EventHandlerConfig] | None = None
    projection_by_stem: dict[str, ProjectionConfig] | None = None
    # Guard-chain wiring: entity name -> the ops/roles its guarded routes
    # declare (drives controller decoration; None/absent = unguarded).
    guards_by_entity: dict[str, ControllerGuards] | None = None
    contracts_by_entity: dict[str, ControllerContract] | None = None
    flag_gates_by_entity: dict[str, ControllerFlagGates] | None = None
    # Audit write-hook wiring: entity name -> the ops its wired audit log
    # records (None/absent = unaudited).
    audit_by_entity: dict[str, ControllerAuditHooks] | None = None


@dataclass(frozen=True, slots=True)
class VerbSpec:
    """Declarative description of one framework generator verb.

    Attributes:
        verb: Framework generator verb resolved through ``cli_bridge``.
        staging_dir: Per-run staging subdirectory name under ``.staging``.
        dest_sub: Destination path (relative to the generated ``src/app``
            project root) where produced files are committed.
        reconcile: Optional callback ``(text, produced_path, ctx) -> text``
            applied to each produced file before it is committed. Absent for
            generators whose output is already lint/format-clean.
    """

    verb: str
    staging_dir: str
    dest_sub: str
    reconcile: Callable[[str, Path, ReconcileContext], str] | None = None
    # When True the reconciled file is passed through `ruff check --fix`
    # before commit, for generators whose templates emit lint noise that the
    # deterministic reconciler does not bother rewriting by hand.
    ruff_autofix: bool = False


# ── Reconcile adapters — adapt the module-specific reconcilers to the uniform
# ``(text, produced_path, ctx) -> text`` signature. ──────────────────────────


def _reconcile_model(text: str, produced: Path, ctx: ReconcileContext) -> str:
    entity = ctx.entity_by_stem.get(produced.stem)
    return reconcile_model(text, entity).text if entity is not None else text


def _reconcile_task(text: str, produced: Path, ctx: ReconcileContext) -> str:
    del produced, ctx
    return reconcile_task(text).text


def _reconcile_webhook(text: str, produced: Path, ctx: ReconcileContext) -> str:
    del produced, ctx
    return reconcile_webhook(text).text


def _reconcile_event(text: str, produced: Path, ctx: ReconcileContext) -> str:
    del produced, ctx
    return reconcile_event(text).text


def _reconcile_event_handler(text: str, produced: Path, ctx: ReconcileContext) -> str:
    handlers = ctx.event_handler_by_stem or {}
    handler = handlers.get(produced.stem)
    if handler is None or not handler.event:
        return text
    handler_snake = produced.name.removesuffix("_handler.py")
    return reconcile_event_handler(
        text,
        handler_snake=handler_snake,
        event_snake=handler.event,
    ).text


def _reconcile_cqrs(text: str, produced: Path, ctx: ReconcileContext) -> str:
    """Repair the command/query generator output (same ``uuid`` F821 defect
    as the event generator; ``UUID`` is already imported)."""
    del produced, ctx
    return reconcile_event(text).text


def _reconcile_projection(text: str, produced: Path, ctx: ReconcileContext) -> str:
    """Fill the projection's ``handles`` set from its wired event nodes."""
    projections = ctx.projection_by_stem or {}
    projection = projections.get(produced.stem)
    if projection is None or not projection.events:
        return text
    return reconcile_projection(text, projection.events).text


def _reconcile_seeder(text: str, produced: Path, ctx: ReconcileContext) -> str:
    entity = ctx.entity_by_stem.get(produced.stem)
    seed = entity.seed_data if entity is not None else ()
    return reconcile_seeder(text, seed_data=seed).text


def _reconcile_exception_filter(text: str, produced: Path, ctx: ReconcileContext) -> str:
    del produced, ctx
    return reconcile_exception_filter(text).text


def _reconcile_error(text: str, produced: Path, ctx: ReconcileContext) -> str:
    del produced, ctx
    return reconcile_error(text).text


def _reconcile_channel(text: str, produced: Path, ctx: ReconcileContext) -> str:
    channel = ctx.channel_by_stem.get(produced.stem)
    if channel is None:
        return text
    return reconcile_channel(text, path=channel.path).text


def _reconcile_guard(text: str, produced: Path, ctx: ReconcileContext) -> str:
    del produced, ctx
    return reconcile_guard(text)


def _reconcile_controller(text: str, produced: Path, ctx: ReconcileContext) -> str:
    entity_name = produced.name.removesuffix("_controller.py")
    text = reconcile_controller(
        text,
        entity_name=entity_name,
        pascal=pascal_case(entity_name),
    ).text
    # Contract wiring (Workstream C): routes wired to contract nodes swap
    # the auto-derived Create/Update DTOs for the contract models.
    wiring = (ctx.contracts_by_entity or {}).get(entity_name)
    if wiring is not None:
        text = apply_contract(text, wiring)
    # Feature-flag gating (nodes plan N2.1): routes wired to enabled flags
    # check the DI-injected FlagManager before the handler body runs.
    gates = (ctx.flag_gates_by_entity or {}).get(entity_name)
    if gates is not None:
        text = apply_flag_gates(text, gates)
    # Guard-chain decoration: routes wired to auth/role nodes decorate the
    # entity's controller handlers with require_auth/require_roles.
    guards = (ctx.guards_by_entity or {}).get(entity_name)
    if guards is not None:
        text = apply_guards(text, guards)
    # Audit write hooks (nodes plan N4.1): routes wired to an audit_log node
    # record create/update/delete mutations through a DI-injected audit
    # repository. Runs last so the hook sees the fully reconciled ctor.
    audit = (ctx.audit_by_entity or {}).get(entity_name)
    if audit is not None:
        text = apply_audit(text, audit)
    return text


def _reconcile_graphql(text: str, produced: Path, ctx: ReconcileContext) -> str:
    del produced, ctx
    return reconcile_graphql(text).text


def _reconcile_health(text: str, produced: Path, ctx: ReconcileContext) -> str:
    pascal = pascal_case(produced.stem)
    return reconcile_health(text, pascal=pascal, critical=True).text


# ── The verb registry ───────────────────────────────────────────────────────
# Bespoke generators (model/repository/migration/controller/task/webhook/
# websocket/middleware) keep their own invocation loops in the writer, but
# their staging/destination/reconcile are declared here so the copy phase is
# fully data-driven. Uniform generators (service/seeder/error/exception_filter/
# cache_repo) are driven entirely from this table.

VERB_SPECS: dict[str, VerbSpec] = {
    spec.verb: spec
    for spec in (
        VerbSpec("model", "models", "src/app/models", reconcile=_reconcile_model),
        VerbSpec("repository", "repositories", "src/app/repositories"),
        VerbSpec("migration", "migrations", "migrations/versions"),
        VerbSpec(
            "controller", "controllers", "src/app/controllers",
            reconcile=_reconcile_controller,
        ),
        VerbSpec(
            "resource", "controllers", "src/app/controllers",
            reconcile=_reconcile_controller,
        ),
        VerbSpec("middleware", "middleware", "src/app/middleware"),
        VerbSpec("task", "tasks", "src/app/tasks", reconcile=_reconcile_task),
        VerbSpec("webhook", "webhooks", "src/app/webhooks", reconcile=_reconcile_webhook),
        VerbSpec(
            "websocket", "channels", "src/app/channels", reconcile=_reconcile_channel
        ),
        VerbSpec("service", "services", "src/app/services"),
        VerbSpec("seeder", "seeders", "src/app/seeders", reconcile=_reconcile_seeder),
        VerbSpec(
            "exception_filter", "filters", "src/app/filters",
            reconcile=_reconcile_exception_filter,
        ),
        VerbSpec("error", "errors", "src/app/errors", reconcile=_reconcile_error),
        VerbSpec("cache_repo", "caches", "src/app/caches"),
        VerbSpec(
            "graphql", "graphql", "src/app/graphql",
            reconcile=_reconcile_graphql, ruff_autofix=True,
        ),
        VerbSpec(
            "event", "events", "src/app/events",
            reconcile=_reconcile_event, ruff_autofix=True,
        ),
        VerbSpec(
            "event_handler", "event_handlers", "src/app/handlers",
            reconcile=_reconcile_event_handler,
        ),
        VerbSpec(
            "command", "commands", "src/app/commands",
            reconcile=_reconcile_cqrs, ruff_autofix=True,
        ),
        VerbSpec(
            "query", "queries", "src/app/queries",
            reconcile=_reconcile_cqrs, ruff_autofix=True,
        ),
        VerbSpec(
            "projection", "projections", "src/app/projections",
            reconcile=_reconcile_projection,
        ),
        VerbSpec("metric", "metrics", "src/app/metrics"),
        VerbSpec("saga", "sagas", "src/app/sagas"),
        VerbSpec("interceptor", "interceptors", "src/app/interceptors"),
        VerbSpec("dataloader", "dataloaders", "src/app/graphql/dataloaders"),
        VerbSpec("auth_policy", "auth_policies", "src/app/policies"),
        VerbSpec("api_client", "clients", "src/app/clients"),
        VerbSpec("storage_driver", "storage", "src/app/storage/backends"),
        VerbSpec(
            "health", "healthchecks", "src/app/healthchecks",
            reconcile=_reconcile_health, ruff_autofix=True,
        ),
        # lexigram-features `feature_flag` generator: one <Name>Flag
        # definition module per flag node (canonical key + default rollout).
        VerbSpec("feature_flag", "features", "src/app/features"),
        # lexigram-auth guard scaffolds: one <Name>AuthGuard definition per
        # auth node and one <Name>Guard (RoleGuard variant) per role node.
        VerbSpec(
            "auth_guard", "auth_guards", "src/app/guards", reconcile=_reconcile_guard
        ),
        VerbSpec("guard", "guards", "src/app/guards", reconcile=_reconcile_guard),
    )
}


def staging_dirs(staging_root: Path) -> dict[str, Path]:
    """Return ``{verb: staging_path}`` for every registered verb, created."""
    dirs = {verb: staging_root / spec.staging_dir for verb, spec in VERB_SPECS.items()}
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def reconcile_text(verb: str, text: str, produced: Path, ctx: ReconcileContext) -> str:
    """Apply the verb's registered reconciler (no-op when none registered)."""
    spec = VERB_SPECS.get(verb)
    if spec is not None and spec.reconcile is not None:
        return spec.reconcile(text, produced, ctx)
    return text


def dest_for(verb: str) -> str:
    """Return the generated-project destination subpath for *verb*."""
    return VERB_SPECS[verb].dest_sub


def autofix_for(verb: str) -> bool:
    """Return True when the verb's output is passed through ruff --fix."""
    spec = VERB_SPECS.get(verb)
    return spec is not None and spec.ruff_autofix


# ── Entity-attached generators ──────────────────────────────────────────────
# Verbs driven by an ``entity -> <node>`` edge; each is invoked with the
# entity name and its ``fields_str``. The node's own config supplies extra
# kwargs via :data:`ENTITY_ATTACHED_EXTRA_KWARGS`; entries map the node kind to
# the framework verb.

ENTITY_ATTACHED: dict[str, str] = {
    "service": "service",
    "seeder": "seeder",
    "error": "error",
    "cache": "cache_repo",
    "graphql": "graphql",
    "health": "health",
}


# Whether each entity-attached verb accepts a ``doc`` kwarg on its
# ``generate`` method. Only verbs that accept a kwarg may pass it; the verbs
# all absorb ``fields_str`` / ``force`` directly or via ``**options``.
_ENTITY_VERB_DOC: dict[str, bool] = {
    "service": False,
    "seeder": False,
    "error": True,
    "cache": False,
    "graphql": False,
    "health": False,
}


def entity_attached_extra_kwargs(kind: str, node_config: Any) -> dict[str, Any]:
    """Build verb-specific kwargs from the wired node's config.

    Only kwargs the generator's ``generate`` accepts are returned (unknown
    kwargs raise ``TypeError``).
    """
    if kind == "error" and _ENTITY_VERB_DOC.get(kind, False):
        description = getattr(node_config, "description", "") or ""
        return {
            "status_code": getattr(node_config, "status_code", 400),
            "error_code": getattr(node_config, "error_code", "") or None,
            "doc": description
            or f"{getattr(node_config, 'name', 'domain')} domain error.",
        }
    if kind == "health":
        return {"critical": bool(getattr(node_config, "critical", True))}
    return {}
