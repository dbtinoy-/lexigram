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
  ``exception_filter``). Drives destination mapping and per-file
  reconciliation; staging is the destination now (OQ-L5), so a verb no
  longer names a staging directory of its own.
* :data:`ENTITY_ATTACHED_VERBS` — the verbs that are driven by an
  ``entity -> <node>`` edge and take the entity's ``fields_str``; the writer
  collects their targets uniformly from edges.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
from lexigram.builder.gen.layout import (
    DEFAULT_LAYOUT,
    WriterLayout,
    component_directory,
)
from lexigram.builder.graph.models import (
    ChannelConfig,
    EntityConfig,
    EventHandlerConfig,
    ProjectionConfig,
)
from lexigram.contracts.cli.generators import pascal_case


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
    # Structure the run is writing for. Reconcilers that rewrite imports
    # need the module-path map, not just paths; without it they would
    # silently emit minimal-layout imports into a structured project.
    layout: WriterLayout | None = None
    module: str | None = None

    @property
    def mods(self) -> dict[str, str]:
        """Dotted import paths for this run's structure."""
        layout = self.layout or DEFAULT_LAYOUT
        return layout.module_names(module=self.module)


@dataclass(frozen=True, slots=True)
class VerbSpec:
    """Declarative description of one framework generator verb.

    Attributes:
        verb: Framework generator verb resolved through ``cli_bridge``.
        default_output_dir: The contributor-declared default output
            directory for this generator (``src/models``,
            ``migrations/versions``, ``seeds``, ``src``). It is *not* a
            destination: :class:`lexigram.builder.gen.layout.WriterLayout`
            maps it onto the active project structure. Values are validated
            against the canonical map by
            ``lexigram.cli.layout.validate_definition``.
        component: Builder-owned component to resolve through instead of
            the canonical map, for the documented deviations where the
            canonical location would change the *runtime* contract rather
            than a directory name. Still layout-resolved -- the deviation is
            which package, never which structure. Exactly one exists today
            (``seeder`` -> ``seeders``); a test pins that count.
        reconcile: Optional callback ``(text, produced_path, ctx) -> text``
            applied to each produced file before it is committed. Absent for
            generators whose output is already lint/format-clean.
    """

    verb: str
    default_output_dir: str
    component: str | None = None
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
    return reconcile_projection(text, projection.events, ctx.mods).text


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
        mods=ctx.mods,
    ).text
    # Contract wiring (Workstream C): routes wired to contract nodes swap
    # the auto-derived Create/Update DTOs for the contract models.
    wiring = (ctx.contracts_by_entity or {}).get(entity_name)
    if wiring is not None:
        text = apply_contract(text, wiring, ctx.mods)
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
# their destination/reconcile are declared here so the copy phase is
# fully data-driven. Uniform generators (service/seeder/error/exception_filter/
# cache_repo) are driven entirely from this table.

VERB_SPECS: dict[str, VerbSpec] = {
    spec.verb: spec
    for spec in (
        VerbSpec("model", "src/models", reconcile=_reconcile_model),
        VerbSpec("repository", "src/repositories"),
        VerbSpec("migration", "migrations/versions"),
        VerbSpec(
            "controller", "src/controllers",
            reconcile=_reconcile_controller,
        ),
        VerbSpec(
            "resource", "src",
            reconcile=_reconcile_controller,
        ),
        VerbSpec("middleware", "src/middleware"),
        VerbSpec("task", "src/tasks", reconcile=_reconcile_task),
        VerbSpec("webhook", "src/webhooks", reconcile=_reconcile_webhook),
        VerbSpec(
            "websocket", "src/websocket", reconcile=_reconcile_channel
        ),
        VerbSpec("service", "src/services"),
        VerbSpec(
            # DEVIATION: canonical is the project-root ``seeds/`` package,
            # which is not importable from the app package. The generated
            # PersistenceProvider imports seeders at boot, so adopting it
            # would break the runtime contract, not just the path (OQ-L1 in
            # docs/09-01-2026/02-LAYOUT_ENGINE.md). The deviation is the
            # *directory*, not the layout: ``seeders`` is a builder-owned
            # component, so it follows the structure like every other
            # package instead of being pinned to ``src/app/seeders``.
            "seeder", "seeds",
            component="seeders",
            reconcile=_reconcile_seeder,
        ),
        VerbSpec(
            "exception_filter", "src/filters",
            reconcile=_reconcile_exception_filter,
        ),
        VerbSpec("error", "src/errors", reconcile=_reconcile_error),
        VerbSpec("cache_repo", "src/repositories"),
        VerbSpec(
            "graphql", "src/schema",
            reconcile=_reconcile_graphql, ruff_autofix=True,
        ),
        VerbSpec(
            "event", "src/events",
            reconcile=_reconcile_event, ruff_autofix=True,
        ),
        VerbSpec(
            "event_handler", "src/handlers",
            reconcile=_reconcile_event_handler,
        ),
        VerbSpec(
            "command", "src/commands",
            reconcile=_reconcile_cqrs, ruff_autofix=True,
        ),
        VerbSpec(
            "query", "src/queries",
            reconcile=_reconcile_cqrs, ruff_autofix=True,
        ),
        VerbSpec(
            "projection", "src/projections",
            reconcile=_reconcile_projection,
        ),
        VerbSpec("metric", "src/metrics"),
        VerbSpec("saga", "src/sagas"),
        VerbSpec("interceptor", "src/interceptors"),
        VerbSpec("dataloader", "src/schema/dataloaders"),
        VerbSpec("auth_policy", "src/policies"),
        VerbSpec("api_client", "src/clients"),
        VerbSpec("storage_driver", "src/storage/backends"),
        VerbSpec(
            "health", "src/health",
            reconcile=_reconcile_health, ruff_autofix=True,
        ),
        # lexigram-features `feature_flag` generator: one <Name>Flag
        # definition module per flag node (canonical key + default rollout).
        VerbSpec("feature_flag", "src/features"),
        # lexigram-auth guard scaffolds: one <Name>AuthGuard definition per
        # auth node and one <Name>Guard (RoleGuard variant) per role node.
        VerbSpec(
            "auth_guard", "src/guards", reconcile=_reconcile_guard
        ),
        VerbSpec("guard", "src/guards", reconcile=_reconcile_guard),
    )
}


def reconcile_text(verb: str, text: str, produced: Path, ctx: ReconcileContext) -> str:
    """Apply the verb's registered reconciler (no-op when none registered)."""
    spec = VERB_SPECS.get(verb)
    if spec is not None and spec.reconcile is not None:
        return spec.reconcile(text, produced, ctx)
    return text


def dest_for(
    verb: str,
    layout: WriterLayout | None = None,
    *,
    module: str | None = None,
) -> str:
    """Return the destination subpath for *verb* under *layout*.

    Args:
        verb: Registered generator verb.
        layout: Project layout; defaults to the minimal single-package
            layout, which reproduces the writer's historical paths.
        module: Bounded-context slug (modular structure only).
    """
    # ``resource`` declares ``src`` upstream and delegates to the controller
    # generator, so ``resolve_output_dir`` hands back the *base* package for
    # the generator to append to. The writer commits produced files directly,
    # so resolve it as the controller component instead.
    resolved = "controller" if verb == "resource" else verb
    spec = VERB_SPECS[resolved]
    active = layout or DEFAULT_LAYOUT
    if spec.component is not None:
        return component_directory(spec.component, active, module=module)
    return active.dest(spec.default_output_dir, generator=resolved, module=module)


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


# ── Standalone node runs ────────────────────────────────────────────────────
# Most node kinds are generated by the same three lines: take the config's
# name, add a couple of verb-specific kwargs, force-write. Repeating that
# eleven times in the writer is how a loop ends up without an attribution
# wrapper -- which is exactly the bug this table removes the room for
# (MODULAR-1). The verb-specific part is the only part that differs, so it
# is the only part declared.

STANDALONE_NODE_KWARGS: dict[str, Callable[[Any], dict[str, Any]]] = {
    "metric": lambda _cfg: {},
    "saga": lambda _cfg: {},
    "feature_flag": lambda _cfg: {},
    "auth_guard": lambda _cfg: {},
    "auth_policy": lambda _cfg: {},
    "guard": lambda _cfg: {"type": "role"},
    "interceptor": lambda cfg: {"doc": cfg.description or None},
    "dataloader": lambda cfg: {"key_type": cfg.key_type},
    "api_client": lambda cfg: {"auth": cfg.auth_type},
    "storage_driver": lambda cfg: {"driver_type": cfg.driver_type},
    "exception_filter": lambda cfg: {
        "exception_type": cfg.exception_type,
        "status_code": cfg.status_code,
        "doc": cfg.description or f"Exception filter {cfg.name}.",
    },
}
"""Verb -> extra kwargs for a one-config-one-module generator run."""
