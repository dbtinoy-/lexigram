"""Provider decomposition for the modular structure (G3).

Under minimal and structured, one `PersistenceProvider` binds every
repository in the project and runs `alembic upgrade head` in its `boot()`.
Those are two unrelated jobs that happen to share a file, and modular is
where the seam has to be cut:

* **Migrations are global.** One database, one schema, one upgrade — no
  matter how many bounded contexts exist. Running them per module would
  race, and "applied exactly once" is the gate.
* **Repository binding is local.** A module's repositories belong to that
  module's provider, registered through its `@module()` boundary rather
  than a central `add_providers()` call. That is the entire point of the
  boundary: a module carries its own wiring, so deleting the module deletes
  the wiring with it.

Entities with no module land in the shared provider
(`shared/di/persistence.py`). The CLI scaffold reserves a `shared/providers/`
package for this; we emit into `shared/di/` instead, because that is where
every lexigram subsystem keeps its DI provider and a generated app should
read like the framework it runs on (OQ-L3, and the upstream row proposal in
`docs/upstream/2026-09-02-component-rows.md`).

Everything here is a pure function from the graph to file contents, so the
writer stays an orchestrator. That is also the shape G8 asks for.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.builder.gen.emitters.context import pascal_entity
from lexigram.builder.gen.layout import WriterLayout
from lexigram.builder.graph.models import EntityConfig, GraphDocument
from lexigram.builder.graph.modules import derive_modules
from lexigram.cli.scaffold import (  # noqa: PLC2701 -- see _framework_imports
    _module_imports,
)

#: Feature tokens to interrogate upstream's import table with. Passing a
#: name it does not know is harmless -- ``_module_imports`` simply emits
#: nothing for it -- so this errs generous on purpose: a token missing here
#: costs a fallback guess, while a token wrongly present costs nothing.
_CLI_FEATURES: frozenset[str] = frozenset(
    {
        "admin",
        "audit",
        "auth",
        "cache",
        "events",
        "features",
        "graphql",
        "http",
        "monitor",
        "notification",
        "queue",
        "search",
        "sql",
        "storage",
        "tasks",
        "tenancy",
        "vector",
        "web",
        "workflow",
    }
)

SHARED = None
"""Key used for bindings that belong to no bounded context.

Note that **entities never use it**. Under modular, ``models``,
``repositories`` and ``services`` are module-local in the canonical layout —
there is no ``shared/repositories/`` for an unscoped entity to land in, and
``resolve_output_dir`` refuses outright. The validator rejects the graph
first (``module.scope_required``); this key exists for kinds that genuinely
can be shared.
"""

#: Framework modules the composition root configures itself, with arguments
#: infrastructure cannot know (``WebModule`` needs ``discover=``). Listing
#: them here as well would register them twice.
_COMPOSITION_ROOT_MODULES: frozenset[str] = frozenset({"WebModule"})


@dataclass(frozen=True, slots=True)
class RepositoryBinding:
    """One repository a provider is responsible for.

    Attributes:
        class_name: Generated class, e.g. ``OrderRepository``.
        import_path: Dotted module it is imported from.
    """

    class_name: str
    import_path: str


def repository_bindings(
    document: GraphDocument, layout: WriterLayout
) -> dict[str | None, tuple[RepositoryBinding, ...]]:
    """Partition every entity repository by the provider that binds it.

    Scope is resolved through :meth:`WriterLayout.effective_module`, not by
    reading ``node.module`` directly — so a repository cannot be bound by a
    module provider while its file was written to the shared layer (G5).

    Returns:
        ``{module slug or None: bindings}``, each tuple sorted by class
        name so regeneration is byte-stable.
    """
    grouped: dict[str | None, list[RepositoryBinding]] = {}
    for node in document.nodes:
        if node.kind != "entity" or not isinstance(node.config, EntityConfig):
            continue
        slug = layout.effective_module(node.kind, node.module)
        names = layout.module_names(module=slug)
        package = names.get("repositories")
        if package is None:
            continue
        entity = pascal_entity(node.config.name)
        grouped.setdefault(slug, []).append(
            RepositoryBinding(
                class_name=f"{entity}Repository",
                import_path=f"{package}.{node.config.name}_repository",
            )
        )
    return {
        slug: tuple(sorted(bindings, key=lambda b: b.class_name))
        for slug, bindings in grouped.items()
    }


def framework_modules(document: GraphDocument) -> tuple[str, ...]:
    """Framework DI modules the graph implies, e.g. ``DatabaseModule``.

    ``derive_modules`` already decides which framework capabilities a graph
    turns on; this filters that to the ones that are actually DI modules.
    Several cards name a helper class instead (``FlagManager``,
    ``Mailable``, ``AbstractDriver``) — calling ``.configure()`` on those
    would not compile, so the name has to earn its place by ending in
    ``Module`` rather than by appearing in a hand-kept list.
    """
    return tuple(
        sorted(
            card.lexigram
            for card in derive_modules(document)
            if card.on
            and card.lexigram.endswith("Module")
            and card.lexigram not in _COMPOSITION_ROOT_MODULES
        )
    )


def emit_infrastructure(document: GraphDocument, *, app_package: str) -> str:
    """Return ``infrastructure/__init__.py``.

    Fills in the empty ``infrastructure_modules()`` the CLI scaffolds, and
    is the one place migrations run.
    """
    modules = framework_modules(document)
    imports = "\n".join(_framework_imports(modules))
    entries = "".join(
        f"        {m}.configure(),\n" for m in modules if m != "DatabaseModule"
    )
    # Migrations are the framework's job, not ours. `DatabaseModule` already
    # owns an AlembicManager and will upgrade to head on boot when asked --
    # so asking is the whole implementation, and it is one call rather than a
    # hand-rolled provider that shells into alembic from a worker thread.
    # Exactly one module configures the database, so "applied exactly once"
    # is a property of the wiring instead of something to be careful about.
    database = (
        "        DatabaseModule.configure(\n"
        "            config=_APP_DATABASE_URL,\n"
        "            enable_migrations=True,\n"
        "        ),\n"
        if "DatabaseModule" in modules
        else ""
    )

    return f'''"""Shared infrastructure wiring for {app_package}.

Feature modules configured here (persistence, auth, cache, tasks, queue,
monitoring) are registered before the web surface and the bounded contexts
in ``src/{app_package}/modules/``.  Replace or extend entries here when you
swap backends.

Database migrations run here and nowhere else: one database means one
``alembic upgrade head``, however many bounded contexts the application has.
"""

from __future__ import annotations

from lexigram.di.module import DynamicModule
{imports}

from {app_package}.config import DATABASE_URL as _APP_DATABASE_URL


def infrastructure_modules() -> list[DynamicModule]:
    """Return the configured infrastructure modules for this application."""
    modules: list[DynamicModule] = [
{database}{entries}    ]

    return modules
'''


def emit_persistence_provider(
    bindings: tuple[RepositoryBinding, ...],
    *,
    class_name: str,
    provider_name: str,
    docstring: str,
    priority: str = "INFRASTRUCTURE",
) -> str:
    """Return a provider that binds *bindings* to the resolved database.

    Shared and per-module providers differ only in name, priority and which
    repositories they own, so they are the same renderer. Two renderers
    would be two places for the binding protocol to drift.
    """
    imports = "\n".join(f"from {b.import_path} import {b.class_name}" for b in bindings)
    reservations = (
        "\n".join(
            f"        container.singleton({b.class_name}, None)" for b in bindings
        )
        or "        return"
    )
    binds = "\n".join(
        f"        container.bind({b.class_name}, {b.class_name}(db_provider))"
        for b in bindings
    )
    boot_body = (
        f"        db_provider = await container.resolve(DatabaseProviderProtocol)\n{binds}"
        if bindings
        else "        return"
    )

    return f'''"""{docstring}"""

from __future__ import annotations

from lexigram.contracts import DatabaseProviderProtocol
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider

{imports}


class {class_name}(Provider):
    """Binds repositories to the resolved database provider."""

    def __init__(self) -> None:
        super().__init__(
            name="{provider_name}", priority=ProviderPriority.{priority}
        )

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Reserve tokens so freeze-time validation sees the dependencies."""
{reservations}

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Replace the reserved tokens with wired instances."""
{boot_body}

    async def shutdown(self) -> None:
        """Tear down resources."""
'''


def _framework_imports(modules: tuple[str, ...]) -> list[str]:
    """Import lines for framework DI modules, taken from upstream's table.

    A class name does not imply its package: ``DatabaseModule`` lives in
    ``lexigram.sql`` and ``MonitorModule`` in ``lexigram.monitor``. This was
    a hand-written guess map, and it was wrong for exactly those two. No
    unit test noticed, because a wrong import string is still a valid
    string -- it fails only when the application boots.

    So the mapping is not maintained here at all. ``_module_imports`` is the
    CLI's own feature-to-import table, the one its scaffold writes from, and
    the answer is read out of it. If upstream moves a module we move with
    it; if upstream renames the helper, the import fails loudly at import
    time rather than producing a subtly broken project.

    A module upstream has no entry for falls back to the old derivation:
    a best-effort import beats silently dropping a capability the graph
    asked for, and `test_framework_imports_are_importable` is what stops
    that fallback from becoming load-bearing.
    """
    known: dict[str, str] = {}
    for feature in _CLI_FEATURES:
        for line in _module_imports(frozenset({feature})):
            _, _, tail = line.partition(" import ")
            for name in (n.strip() for n in tail.split(",")):
                known.setdefault(name, line)

    lines: list[str] = []
    for name in modules:
        line = known.get(name)
        if line is None:
            root = name.removesuffix("Module").lower()
            line = f"from lexigram.{root} import {name}"
        lines.append(line)
    return sorted(set(lines))
