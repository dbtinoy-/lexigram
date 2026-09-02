"""Wiring the writer into the modular structure (G8).

The writer stays an orchestrator: it decides *when* files are produced and
commits them. Deciding *what* a modular project contains, and where a
generated file belongs once bounded contexts exist, lives here — so
``writer.py`` does not grow a second personality every time the structure
gains a feature.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace as dc_replace

from lexigram.builder.gen.emitted import AttributionLedger
from lexigram.builder.gen.emitters.entity_emitter import GENERATED_HEADER
from lexigram.builder.gen.emitters.module_emitter import (
    emit_module_package,
    emit_modules_registry,
    provider_class_name,
)
from lexigram.builder.gen.formatting import autofix_text
from lexigram.builder.gen.layout import WriterLayout
from lexigram.builder.gen.modular.composition import emit_app
from lexigram.builder.gen.modular.providers import (
    _framework_imports,
    emit_infrastructure,
    emit_persistence_provider,
    repository_bindings,
)
from lexigram.builder.gen.node_generators import (
    ReconcileContext,
    autofix_for,
    reconcile_text,
)
from lexigram.builder.gen.staging import StagedFile
from lexigram.builder.graph.models import (
    ModuleConfig,
    ValidatedGraph,
)
from lexigram.builder.graph.modules import module_import_graph
from lexigram.builder.graph.palette import KIND_MODULE


def commit_staged(
    staged: Sequence[StagedFile],
    *,
    files: dict[str, str],
    ledger: AttributionLedger,
    reconcile_ctx: ReconcileContext,
) -> None:
    """Move every staged generator output to its destination.

    Since staging is shaped like the destination (OQ-L5), a staged file's
    path relative to the staging root *is* where it belongs: committing is
    a copy with reconciliation, not a mapping exercise. What used to be
    decided here -- which verb produced a file, which bounded context owns
    it -- is recorded by :class:`StagingArea` as the file appears, so the
    two answers cannot disagree, and the walk has no room for the
    ``controller``/``resource`` collision that came of keying by verb.

    The one decision left is the import roots the reconcilers must name:
    the owning context's (``shop_api.modules.sales.repositories``, not a
    global package that does not exist under modular).
    """
    for file in staged:
        ctx = (
            dc_replace(reconcile_ctx, module=file.module)
            if file.module is not None
            else reconcile_ctx
        )
        text = reconcile_text(
            file.verb, file.path.read_text(encoding="utf-8"), file.path, ctx
        )
        if autofix_for(file.verb):
            text = autofix_text(text, file.path.name)
        files[file.destination] = text
        ledger.record(file.destination, node_id=file.node_id, verb=file.verb)


def emit_modular_project(
    graph: ValidatedGraph,
    files: dict[str, str],
    ledger: AttributionLedger,
    *,
    layout: WriterLayout,
) -> None:
    """Add the modular-only artifacts to *files*.

    Four kinds of file exist only under ``modular``: the composition
    root, the infrastructure wiring, the module registry, and one
    package per bounded context. Everything else the writer emits is
    shared with the other structures and only differs by path, which
    :class:`WriterLayout` already handles.

    Attribution follows the layout plan (L4): a module's boundary files
    belong to its Module node, so selecting the frame on the canvas
    highlights the package it produced. The registry belongs to no
    single node -- it is a function of the whole graph.
    """
    document = graph.document
    package = layout.app_package
    settings = graph.settings()

    files[f"src/{package}/app.py"] = emit_app(
        document, project_name=layout.app_package, app_package=package
    )
    ledger.record(f"src/{package}/app.py", node_id=settings.id)

    infrastructure = f"src/{package}/infrastructure/__init__.py"
    files[infrastructure] = emit_infrastructure(document, app_package=package)
    ledger.record(infrastructure, node_id=settings.id)

    module_nodes = [
        node
        for node in document.nodes
        if node.kind == KIND_MODULE and isinstance(node.config, ModuleConfig)
    ]
    slugs = tuple(node.config.name for node in module_nodes)  # type: ignore[union-attr]

    registry = f"src/{package}/modules/__init__.py"
    files[registry] = emit_modules_registry(slugs, app_package=package)
    # No single owner: the registry is a function of every Module node,
    # so attributing it to one of them would make deleting that node
    # look like it deletes the registry.
    ledger.record(registry, node_id=None)

    node_by_slug = {
        node.config.name: node.id  # type: ignore[union-attr]
        for node in module_nodes
    }
    imports = module_import_graph(document)
    bindings = repository_bindings(document, layout)

    for node in module_nodes:
        config = node.config
        assert isinstance(config, ModuleConfig)
        owned = bindings.get(config.name, ())
        package_files = emit_module_package(
            config,
            app_package=package,
            imports=tuple(sorted(imports.get(config.name, ()))),
            # Only a provider that binds something is worth registering,
            # and only a registered provider actually runs: an unregistered
            # one leaves every repository it binds unresolvable, which
            # surfaces as a 500 on the first request rather than at boot.
            register_provider=bool(owned),
            # Its provider resolves DatabaseProviderProtocol, which is only
            # visible to modules that import the module exporting it.
            framework_imports=(
                ((_framework_imports(("DatabaseModule",))[0], "DatabaseModule"),)
                if owned
                else ()
            ),
        )
        if owned:
            # A module with repositories needs a provider that binds
            # them; the scaffold's bare provider would leave them
            # unresolvable. Modules with none keep the CLI's file, which
            # is what the parity report compares against.
            provider_path = f"src/{package}/modules/{config.name}/provider.py"
            package_files[provider_path] = emit_persistence_provider(
                owned,
                class_name=provider_class_name(config.name),
                provider_name=config.name,
                docstring=f"DI provider for the {config.name} module.",
                priority=config.provider_priority,
            )
        for rel, content in package_files.items():
            files[rel] = content
            ledger.record(rel, node_id=node.id)

    _ensure_packages(files, ledger, package=package, node_by_slug=node_by_slug)


def _ensure_packages(
    files: dict[str, str],
    ledger: AttributionLedger,
    *,
    package: str,
    node_by_slug: dict[str, str],
) -> None:
    """Give every generated module-local directory an ``__init__.py``.

    Under minimal and structured each component directory is a fixed,
    known path and the scaffold writes its ``__init__.py`` outright. Under
    modular the set of directories is a function of the graph -- one
    ``controllers/`` per module that has routes -- so nothing static can
    enumerate them.

    Leaving them out is survivable right up until it is not. Imports still
    work, because Python treats a directory without ``__init__.py`` as a
    namespace package. What breaks is *discovery*: the composition root
    finds controllers by walking ``<app>.modules`` with ``pkgutil``, and a
    namespace package is not walked. The result is an application that
    boots, reports itself started, and answers 404 on every route the user
    drew -- the failure mode this structure keeps producing, where the
    parts are all present and simply not connected.
    """
    roots = (f"src/{package}/modules/", f"src/{package}/shared/")
    needed: set[str] = set()
    for rel in list(files):
        if not rel.startswith(roots):
            continue
        parts = rel.split("/")
        for depth in range(3, len(parts)):
            directory = "/".join(parts[:depth])
            needed.add(f"{directory}/__init__.py")

    for init in sorted(needed - set(files)):
        files[init] = GENERATED_HEADER
        # The package belongs to the module whose directory it is, so
        # deleting that Module node takes its packages with it.
        slug = init.split("/")[3] if "/modules/" in init else None
        ledger.record(init, node_id=node_by_slug.get(slug or ""))
