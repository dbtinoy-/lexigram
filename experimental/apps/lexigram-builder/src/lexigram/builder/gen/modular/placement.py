"""Which bounded context owns a generated file (Phase F, MODULAR-1/2).

:class:`~lexigram.builder.gen.layout.WriterLayout` knows every rule about
paths except one: under ``modular`` a component has no single destination.
``order_repository.py`` belongs to *sales*, ``invoice_repository.py`` to
*billing*, and both are ``repositories``. The layout cannot answer that on
its own because the answer is in the graph, not in the structure.

:class:`Placement` is that missing half. It is built once from the validated
graph and passed to the emitters, which ask it two questions:

* *where does this config's file go?* — :meth:`Placement.dest`
* *what are this config's imports called?* — :meth:`Placement.imports`

Outside ``modular`` every answer collapses to the single global one, so an
emitter written against ``Placement`` behaves exactly as before — that is
deliberate, and it is what keeps the golden manifests for minimal and
structured projects byte-identical.

Why a config and not a node: emitters receive configs, and edge resolution
(``resolve_cqrs``, ``resolve_projections``, ``resolve_handlers``) *rebuilds*
some of them, so object identity alone loses the owner. The index therefore
answers by identity first and by (config type, name) second — the pair a
rebuilt config preserves, and the pair a user would use to say which node
they meant.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence

from lexigram.builder.gen.layout import WriterLayout
from lexigram.builder.gen.node_generators import dest_for
from lexigram.builder.graph.models import GraphDocument, ValidatedGraph

__all__ = ["Placement"]


def _identity(config: object) -> tuple[str, str]:
    """Config key that survives a rebuild: its type and its name."""
    return (type(config).__name__, str(getattr(config, "name", "")))


class Placement(Mapping[str, str]):
    """Destination and import roots, resolved per config.

    Also a ``Mapping`` of the *global* import roots, so the many emitter
    sites that name a cross-cutting package (``mods['app']``,
    ``mods['di']``) keep working unchanged: only the sites that name a
    module-local package have to say which config they are placing.
    """

    def __init__(
        self,
        layout: WriterLayout,
        *,
        by_id: Mapping[int, str | None] | None = None,
        by_name: Mapping[tuple[str, str], str | None] | None = None,
        by_node: Mapping[str, str | None] | None = None,
    ) -> None:
        self._layout = layout
        self._by_id = dict(by_id or {})
        self._by_name = dict(by_name or {})
        self._by_node = dict(by_node or {})
        self._mods_cache: dict[str | None, dict[str, str]] = {}

    # ── construction ──────────────────────────────────────────────────

    @classmethod
    def of(cls, graph: ValidatedGraph, layout: WriterLayout) -> Placement:
        """Index *graph*'s nodes by the module that owns their files.

        Scope is resolved through :meth:`WriterLayout.effective_module`, so
        a cross-cutting kind drawn inside a frame is recorded as unowned —
        the same rule the writer's relocation pass applies, stated once.
        """
        return cls.of_document(graph.document, layout)

    @classmethod
    def of_document(cls, document: GraphDocument, layout: WriterLayout) -> Placement:
        """Index a document's nodes; the preview has no ValidatedGraph."""
        by_id: dict[int, str | None] = {}
        by_name: dict[tuple[str, str], str | None] = {}
        by_node: dict[str, str | None] = {}
        for node in document.nodes:
            config = node.config
            if config is None:
                continue
            slug = layout.effective_module(node.kind, node.module)
            by_id[id(config)] = slug
            by_node[node.id] = slug
            key = _identity(config)
            # First writer wins: two nodes of one kind sharing a name is a
            # validation error, so a collision here can only be a config
            # type reused across kinds, where the earlier node is as good
            # an answer as the later one and stability beats recency.
            by_name.setdefault(key, slug)
        return cls(layout, by_id=by_id, by_name=by_name, by_node=by_node)

    @classmethod
    def unscoped(cls, layout: WriterLayout) -> Placement:
        """A placement that owns nothing — every answer is the global one.

        For callers that have a layout but no graph (tests, the CLI parity
        harness): every component lands at the app root, which is exactly
        what a project with no bounded contexts looks like.
        """
        return cls(layout)

    # ── the two questions ─────────────────────────────────────────────

    def module_of(self, config: object | None) -> str | None:
        """Slug of the bounded context that owns *config*'s files.

        A ``str`` is read as a node id, for the callers that hold the
        attribution (which node caused this file) but not the config --
        merged configs, for instance, are rebuilt from several nodes.
        """
        if config is None:
            return None
        if isinstance(config, str):
            return self._by_node.get(config)
        found = self._by_id.get(id(config))
        if found is not None:
            return found
        if id(config) in self._by_id:
            return None
        return self._by_name.get(_identity(config))

    def dest(self, verb: str, config: object | None = None) -> str:
        """Project-relative directory for *verb*'s output owning *config*."""
        return dest_for(verb, self._layout, module=self.module_of(config))

    def pkg(self, name: str, *parts: str, config: object | None = None) -> str:
        """Path inside a builder-owned package, scoped to *config*'s module."""
        return self._layout.pkg(name, *parts, module=self.module_of(config))

    def imports(self, config: object | None = None) -> dict[str, str]:
        """Import roots as seen from the module that owns *config*."""
        return self._imports_for(self.module_of(config))

    def _imports_for(self, slug: str | None) -> dict[str, str]:
        cached = self._mods_cache.get(slug)
        if cached is None:
            cached = self._layout.module_names(module=slug)
            self._mods_cache[slug] = cached
        return cached

    def imports_named(
        self, type_name: str, name: str, *, fallback: object | None = None
    ) -> dict[str, str]:
        """Import roots for a config referred to only by name.

        Some generated code names a peer it never receives -- a projection
        subscribes to `order_placed` without holding the event's config. The
        (type, name) pair is what the author wrote, so it is what the lookup
        uses. When nothing declares that name, *fallback* decides -- an
        event only a projection mentions belongs where the projection does,
        since that is the only context that knows about it.
        """
        key = (type_name, name)
        slug = (
            self._by_name[key]
            if key in self._by_name
            else self.module_of(fallback)
        )
        return self._imports_for(slug)

    def group(
        self,
        configs: Iterable[object],
        *,
        owner: Callable[[object], object] | None = None,
    ) -> list[tuple[str | None, list[object]]]:
        """Partition *configs* by owning module, shared group first.

        The unit of emission for anything a component package aggregates:
        under ``modular`` a package ``__init__`` exists once per owning
        context and re-exports only that context's members, and outside it
        this yields exactly one group, which is the old behaviour.

        *owner* maps a config to the config whose module governs it, for the
        cases where a file exists because of something else: an event a
        handler names without a node of its own belongs to that handler's
        context, not to nowhere.
        """
        grouped: dict[str | None, list[object]] = {}
        for config in configs:
            governing = owner(config) if owner is not None else config
            grouped.setdefault(self.module_of(governing), []).append(config)
        return [
            (slug, grouped[slug])
            for slug in sorted(grouped, key=lambda s: (s is not None, s or ""))
        ]

    def modules(self, configs: Iterable[object]) -> tuple[str | None, ...]:
        """Distinct owning modules of *configs*, shared first."""
        return tuple(slug for slug, _ in self.group(configs))

    # ── Mapping over the global import roots ──────────────────────────

    def __getitem__(self, key: str) -> str:
        return self.imports()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.imports())

    def __len__(self) -> int:
        return len(self.imports())

    @property
    def layout(self) -> WriterLayout:
        return self._layout

    def as_dict(self) -> dict[str, str]:
        """The global import map, for emitters that still take a dict."""
        return dict(self.imports())


def sole(configs: Sequence[object]) -> object | None:
    """First config of a group, or None — a readable ``x[0] if x else None``."""
    return configs[0] if configs else None
