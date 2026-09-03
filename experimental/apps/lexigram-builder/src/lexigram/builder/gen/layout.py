"""Structure-aware path resolution for the project writer.

Single authority for *where* a generated file goes. Every path the writer
commits must come from here, and every answer here comes from
:func:`lexigram.cli.layout.resolve_output_dir` — the framework's own
canonical generator→path map, shared with ``lexigram new project``,
``lexigram gen`` and the alignment gate (``dev/checks/generator_output.py``).

The builder never re-declares that map. A local table would sit outside the
gate and drift the moment a package renames a component package.

There is **one** tree, and a node either belongs to a module or it does not:

``src/<app>/<component>/``
    Feature code that has not been scoped to a bounded context.
``src/<app>/shared/<component>/``
    Cross-cutting components, decided by the kind rather than by the node.
``src/<app>/modules/<slug>/<component>/``
    Feature code scoped to a bounded context.

The project-wide ``minimal``/``structured``/``modular`` mode is gone: it was
a second, coarser answer to a question ``node.module`` already answers, and
it made growth a migration (adopting bounded contexts relocated every file).
Scoping a node now moves that node.

See ``docs/09-02-2026/05-ONE_LAYOUT.md``.
"""

from __future__ import annotations

from collections.abc import Mapping

from dataclasses import dataclass

from lexigram.builder.graph.palette import KIND_COMPONENT, SHARED_KINDS
from lexigram.cli.layout import (
    COMPONENTS,
    MODULES_DIR,
    SHARED_DIR,
    resolve_output_dir,
)

__all__ = [
    "BUILDER_COMPONENTS",
    "MODULES_DIR",
    "PINNED_MODULES",
    "SHARED_DIR",
    "SHARED_OVERRIDES",
    "BuilderComponent",
    "WriterLayout",
    "component_directory",
    "path_hints",
]

#: Components whose destination is pinned regardless of structure, and so
#: whose import path is pinned too. Empty, and worth keeping empty: a pin is
#: a path the layout does not decide, which is the one thing this module
#: exists to prevent. ``seeders`` used to live here (pinned to
#: ``src/app/seeders`` in every structure, OQ-L1) until it was made
#: structure-aware like everything else; the mechanism stays because the
#: next runtime-contract deviation should be *declared* here rather than
#: inlined somewhere as a literal.
PINNED_MODULES: dict[str, str] = {}

#: Canonical components the builder treats as cross-cutting even though the
#: upstream row says module-local, keyed by component directory with the
#: reason. This is a *disagreement made explicit*, not a preference: the two
#: tables cannot both be right, and generation raises where they meet.
#:
#: Each row is proposed upstream and dies when it lands --
#: ``test_anti_drift.py::test_shared_overrides_are_still_needed_upstream``
#: fails the moment the canonical row flips, so the override is deleted by a
#: failing test rather than by someone remembering.
SHARED_OVERRIDES: dict[str, str] = {
    "guards": (
        "An auth guard is a credential check, not a bounded-context "
        "concern: `@require_auth()` decorates controllers in every module, "
        "and the palette agrees -- `auth` and `role` are cross-cutting "
        "kinds whose scope row says shared. With the canonical row saying "
        "module-local, the two meet at generation time and a modular app "
        "containing any Auth Guard or Role node cannot be generated at all "
        "(TASK-6 / MODULAR-3). Proposed upstream "
        "(docs/upstream/2026-09-02-component-rows.md)."
    ),
}


@dataclass(frozen=True, slots=True)
class BuilderComponent:
    """A package the builder emits that the canonical map does not cover.

    These are *not* an escape hatch for inventing paths. The table below is
    closed, every row carries its justification, and
    ``test_layout_alignment.py`` pins the set — a new row cannot appear
    without a reviewer seeing it.

    Attributes:
        directory: Package directory, relative to the structure's root.
        shared: Cross-cutting (``src/<app>/shared/<dir>`` under modular)
            versus module-local (``src/<app>/modules/<m>/<dir>``).
        canonical: Canonical component this package *should* eventually
            fold into, when such a row already exists upstream. Recorded,
            deliberately **not** yet adopted: folding would rename packages
            in the minimal layout and break every generated import that
            names them. Tracked as OQ-L3.

            An upstream row existing is not by itself a reason to fold. The
            test is which name the framework actually uses in its own
            source: `di/` is in 34 packages and stays, while `emails/` is in
            none and should eventually become `notifications/`. A row with
            no `canonical` is either unrepresented upstream or deliberately
            keeping the framework's own spelling.
        why: Why no canonical row applies (or why adoption is deferred).
    """

    directory: str
    shared: bool
    why: str
    canonical: str | None = None


BUILDER_COMPONENTS: dict[str, BuilderComponent] = {
    "di": BuilderComponent(
        directory="di",
        shared=True,
        why=(
            "Late-boot DI providers. `di/` is not a builder invention -- it "
            "is the framework's own convention, unanimously: every lexigram "
            "subsystem with a DI provider keeps it at `<subsystem>/di/"
            "provider.py`, 30 of them, no exceptions. (`lexigram-sql` also "
            "ships a directory whose name reads like an exception, but it "
            "is that package's database *driver* layer -- whatever it ends "
            "up called -- and its DI provider is in `sql/di/` with "
            "everyone else's.) Generated apps should read "
            "like the framework they are built on, so the canonical "
            "`providers` row is the outlier, not this. Proposed upstream "
            "(docs/upstream/2026-09-02-component-rows.md), not folded."
        ),
    ),
    "emails": BuilderComponent(
        directory="emails",
        shared=False,
        canonical="notifications",
        why=(
            "Mailer plus rendered templates. `notifications` is the canonical "
            "home for `notification_template` and the framework backs it "
            "(`lexigram-notification`; no package ships an `emails/`), so "
            "this one really should fold -- but folding renames "
            "`app.emails.*` in every generated import, which is a reviewed "
            "rename step, not a path refactor. Still OQ-L3."
        ),
    ),
    "uploads": BuilderComponent(
        directory="uploads",
        shared=False,
        canonical="storage/backends",
        why=(
            "Per-entity upload storage adapters, which are storage drivers "
            "by another name -- though `lexigram-web` ships its own "
            "`web/uploads/`, so the naming has precedent on both sides. "
            "Fold with `emails` if at all; not urgent. Still OQ-L3."
        ),
    ),
    "seeders": BuilderComponent(
        directory="seeders",
        shared=True,
        why=(
            "Idempotent data seeders. The canonical row is the project-root "
            "`seeds/`, which is not importable -- and the generated "
            "PersistenceProvider imports each seeder at boot, so adopting it "
            "would be a runtime-contract change, not a rename (OQ-L1). "
            "Shared rather than module-local: seeding is a property of the "
            "database, and one database is a program-wide constraint."
        ),
    ),
    "auth": BuilderComponent(
        directory="auth",
        shared=True,
        why=(
            "API-key issuance and verification. No canonical row exists; the "
            "builder has a real generator for it, so propose one upstream."
        ),
    ),
    "contracts": BuilderComponent(
        directory="contracts",
        shared=True,
        why=(
            "Shared request/response schemas. No canonical row exists; "
            "propose one upstream."
        ),
    ),
    "validators": BuilderComponent(
        directory="validators",
        shared=False,
        why=(
            "Per-entity validation rules. No canonical row exists; propose "
            "one upstream."
        ),
    ),
}
"""Builder-owned packages with no adopted canonical component row.

See ``docs/09-01-2026/09-KIND_MAP.md`` §3 and OQ-L3 in
``docs/09-01-2026/02-LAYOUT_ENGINE.md``.
"""


@dataclass(frozen=True, slots=True)
class WriterLayout:
    """Resolves generator verbs to destination paths for one project.

    Attributes:
        app_package: Python package holding the application — always the
            snake_case app name. It used to be the literal ``app`` under the
            minimal structure, which is why two projects could never be
            imported into one process.
    """

    app_package: str = "app"

    @classmethod
    def for_app(cls, app_name: str) -> WriterLayout:
        """Build the layout for an application name."""
        return cls(app_package=app_name)

    @classmethod
    def for_settings(cls, settings: object) -> WriterLayout:
        """Build the layout an app settings config implies.

        Takes the config rather than the document so callers that already
        unpacked settings do not have to re-find the node.
        """
        return cls(app_package=str(getattr(settings, "app_name", "app")))

    # ── scope ─────────────────────────────────────────────────────────

    def effective_module(self, kind: str, module: str | None) -> str | None:
        """The bounded context a node's files actually land in.

        A node's ``module`` field is what the *author* asked for; this is
        what the filesystem will do about it. They differ in one way, and it
        must never be decided ad hoc by a caller: **cross-cutting kinds
        ignore scope**. ``middleware`` lands in ``shared/`` whether or not it
        was dropped inside a frame, because ``COMPONENTS[...].shared`` says
        so upstream. The canvas grouping may still be wanted, so this is not
        an error; the validator warns (``module.shared_kind_scoped``) and the
        path simply does not follow.

        Every caller that turns a node into a path comes through here, so the
        rule is stated once. Getting it wrong per-caller is how a component
        ends up in ``modules/sales/middleware/`` in one code path and
        ``shared/middleware/`` in another.

        Args:
            kind: The node's palette kind.
            module: The slug the author assigned, if any.

        Returns:
            The slug to pass down to :meth:`dest` / :meth:`pkg`, or ``None``
            when the files are not module-local.
        """
        if module is None:
            return None
        # Fail open: only a kind the palette *declares* cross-cutting loses
        # its scope. A kind nobody has classified yet is far more likely to
        # be module-local, and a stranger silently landing in ``shared/`` --
        # visible to every context -- is the harder mistake to notice.
        return None if kind in SHARED_KINDS else module

    # ── paths ─────────────────────────────────────────────────────────

    def dest(
        self,
        default_output_dir: str,
        *,
        generator: str | None = None,
        module: str | None = None,
    ) -> str:
        """Return the project-relative directory for a generator's output.

        Args:
            default_output_dir: The contributor-declared default
                (``src/models``, ``migrations/versions``, ``seeds``, ``src``).
            generator: Generator/verb name — required for the ``src``-root
                generators whose real target differs from their declaration
                (``resource`` delegates to the controller generator).
            module: Bounded-context slug, when the node has one.

        Returns:
            Project-relative destination directory.

        Raises:
            ValueError: Unknown output directory.
        """
        component = (
            default_output_dir[4:]
            if default_output_dir.startswith("src/")
            else None
        )
        if component in SHARED_OVERRIDES and generator != "resource":
            return f"src/{self.app_package}/{SHARED_DIR}/{component}"
        return resolve_output_dir(
            default_output_dir,
            app_package=self.app_package,
            module=module,
            generator=generator,
        )

    def pkg(self, name: str, *parts: str, module: str | None = None) -> str:
        """Path inside a builder-owned package (:data:`BUILDER_COMPONENTS`).

        Mirrors :func:`lexigram.cli.layout.resolve_output_dir` semantics for
        packages the canonical map does not yet cover, so these are placed
        exactly like canonical components are.

        Args:
            name: Key in :data:`BUILDER_COMPONENTS`.
            *parts: Optional path segments appended to the package.
            module: Bounded-context slug, when the node has one.

        Raises:
            KeyError: Unknown package name.
        """
        component = BUILDER_COMPONENTS[name]
        directory = component.directory
        if component.shared:
            base = f"src/{self.app_package}/{SHARED_DIR}/{directory}"
        elif module is None:
            base = f"src/{self.app_package}/{directory}"
        else:
            base = f"src/{self.app_package}/{MODULES_DIR}/{module}/{directory}"
        return "/".join((base, *parts)) if parts else base

    @property
    def src_root(self) -> str:
        """Root directory that component packages sit under: ``src/<app>``."""
        return f"src/{self.app_package}"

    def app_path(self, *parts: str) -> str:
        """Path inside the application package itself.

        Used for composition-root files that belong to no component package
        (``app.py``, ``config.py``, ``di/provider.py``).
        """
        base = f"src/{self.app_package}"
        return "/".join((base, *parts)) if parts else base

    def app_module(self, *parts: str) -> str:
        """Dotted module path inside the application package.

        ``shop_api.config``.
        """
        return ".".join((self.app_package, *parts))

    def component_module(self, default_output_dir: str, **kwargs: object) -> str:
        """Dotted module path of a component package.

        The import-side twin of :meth:`dest`: generated code must import
        from wherever the layout decided to put things, or the project does
        not run. ``shop_api.repositories`` versus
        ``shop_api.modules.sales.repositories``.
        """
        generator = kwargs.get("generator")
        module = kwargs.get("module")
        return self.module_path(
            self.dest(
                default_output_dir,
                generator=generator if isinstance(generator, str) else None,
                module=module if isinstance(module, str) else None,
            )
        )

    def pkg_module(self, name: str, *, module: str | None = None) -> str:
        """Dotted module path of a builder-owned package (``app.di``)."""
        return self.module_path(self.pkg(name, module=module))

    def module_names(self, *, module: str | None = None) -> dict[str, str]:
        """Dotted import paths for every package generated code references.

        Generated code must import from wherever the layout put things --
        ``shop_api.repositories`` unscoped,
        ``shop_api.modules.sales.repositories`` scoped -- or the project does
        not run. Emitters take this
        mapping instead of each re-deriving paths, so a component's import
        path is decided in exactly one place.

        Sourced from the framework's own ``COMPONENTS`` table rather than
        the builder's verb list, so it cannot drift from the canonical map
        (and so this module stays free of a builder-side import cycle).

        Keys are canonical component directories (``controllers``,
        ``schema/dataloaders``), builder-owned package names (``di``,
        ``emails``), and ``"app"`` for the application package.

        Args:
            module: Bounded-context slug, when resolving module-local
                components for one context.
        """
        names: dict[str, str] = {"app": self.app_package}
        for component in COMPONENTS:
            directory = component.structured
            try:
                dest = self.dest(f"src/{directory}", module=module)
            except ValueError:
                continue  # module-local under modular without a module
            names[directory] = self.module_path(dest)
        for name in BUILDER_COMPONENTS:
            try:
                names[name] = self.pkg_module(name, module=module)
            except ValueError:
                continue
        names.update(PINNED_MODULES)
        return names

    @staticmethod
    def module_path(dest: str) -> str:
        """Convert a ``src/``-relative destination to a Python module path.

        ``src/app/websocket`` -> ``app.websocket``. Destinations outside
        ``src/`` (root dirs like ``seeds``) are returned dotted as-is; they
        are importable only from the project root.
        """
        stripped = dest[4:] if dest.startswith("src/") else dest
        return stripped.replace("/", ".")


DEFAULT_LAYOUT = WriterLayout()
"""Fallback layout for callers with no application name in hand."""


# ─── Path hints for the canvas ───────────────────────────────────────────────


def component_directory(
    component: str, layout: WriterLayout, *, module: str | None = None
) -> str:
    """Project-relative directory for *component* under *layout*.

    Three sources, in priority order, none of them a table declared here:

    1. :data:`PINNED_MODULES` -- components whose destination is fixed in
       every structure.
    2. :data:`BUILDER_COMPONENTS` -- packages the canonical map does not
       cover, resolved by :meth:`WriterLayout.pkg`.
    3. the canonical map itself, via :meth:`WriterLayout.dest`.
    """
    if component in PINNED_MODULES:
        return "src/" + PINNED_MODULES[component].replace(".", "/")
    if component in BUILDER_COMPONENTS:
        return layout.pkg(component, module=module)
    return layout.dest(f"src/{component}", module=module)


def path_hints(
    *,
    app_name: str = "app",
    module: str = "<module>",
    extra_components: Mapping[str, str] | None = None,
) -> dict[str, dict[str, str]]:
    """Where each drawable kind's primary file lands, scoped and unscoped.

    The canvas needs to tell the user where a node will end up, and it used
    to do that with hard-coded ``src/app/...`` strings -- a private copy of
    the layout map, free to drift the moment a component moves. This computes
    the same answer the writer will actually use.

    Args:
        app_name: Application package to render the paths against.
        module: Placeholder (or real slug) for the bounded context.
        extra_components: kinds outside :data:`KIND_COMPONENT` -- undrawable
            surfaces that still show a path somewhere in the UI. Passed in
            by the caller rather than declared here: ``KIND_COMPONENT`` is
            pinned to the palette by a contract test, and widening it would
            weaken that gate to describe a UI need.

    Returns:
        ``{kind: {"app": dir, "module": dir}}`` — where the kind lands while
        it belongs to no module, and where it lands once it does. For a
        cross-cutting kind the two are identical, which is how the UI can say
        "scoping this changes nothing" without a second table of rules.
    """
    components = dict(KIND_COMPONENT)
    components.update(extra_components or {})
    layout = WriterLayout.for_app(app_name)
    hints: dict[str, dict[str, str]] = {}
    for kind, component in sorted(components.items()):
        hints[kind] = {
            "app": component_directory(component, layout, module=None),
            "module": component_directory(component, layout, module=module),
        }
    return hints
