"""Emit-time file attribution (task L4).

The writer knows exactly which node it is generating for at the moment it
produces a file — and until now it threw that fact away, leaving
``attribution.py`` to reverse-engineer ownership from the *shape* of minimal
paths with fifteen regexes.

That worked only because there was one layout. Under three structures times
N modules, a path-pattern table becomes combinatorial and silently wrong:
``src/app/models/order.py`` and ``src/shop/modules/sales/models/order.py``
are the same file, and a regex anchored on the former simply stops matching.

So record it instead of deducing it.

Two recording modes, because the writer produces files two ways:

* **direct** — ``files[path] = content``; the owner is known at the call
  site, so :meth:`AttributionLedger.record` takes it directly.
* **observed** — a framework generator writes into a staging directory and
  the writer copies the result. The writer cannot name the files in
  advance, so :meth:`AttributionLedger.observing` snapshots the directory
  around the call and attributes whatever appeared. Exact, and independent
  of both the layout and the generator's naming conventions.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

__all__ = ["AttributionLedger", "EmittedFile"]


@dataclass(frozen=True, slots=True)
class EmittedFile:
    """One generated file and the graph node responsible for it.

    Attributes:
        path: Project-relative path, forward slashes.
        node_id: Owning canvas node, or ``None`` for structural files
            (scaffold, config, composition root) that belong to no node.
        verb: Generator verb that produced it, when one applies.
        module: Bounded-context slug under the modular structure.
    """

    path: str
    node_id: str | None = None
    verb: str | None = None
    module: str | None = None


class AttributionLedger:
    """Collects :class:`EmittedFile` records over one write.

    Ordering is insertion order; :meth:`files_by_node` sorts on the way out
    so persisted tallies compare cleanly across runs.
    """

    __slots__ = ("_records", "_seen")

    def __init__(self) -> None:
        self._records: list[EmittedFile] = []
        self._seen: set[str] = set()

    def __len__(self) -> int:
        return len(self._records)

    @property
    def records(self) -> tuple[EmittedFile, ...]:
        return tuple(self._records)

    def record(
        self,
        path: str,
        *,
        node_id: str | None,
        verb: str | None = None,
        module: str | None = None,
    ) -> None:
        """Attribute *path*. First writer wins on duplicates.

        Re-recording is normal: a file can be staged and later overwritten
        by a reconcile pass. The first attribution is the meaningful one —
        it names the node that caused the file to exist at all.
        """
        norm = path.replace("\\", "/")
        if norm in self._seen:
            return
        self._seen.add(norm)
        self._records.append(
            EmittedFile(path=norm, node_id=node_id, verb=verb, module=module)
        )

    @contextmanager
    def observing(
        self,
        root: Path,
        *,
        node_id: str | None,
        verb: str | None = None,
        module: str | None = None,
        rebase: str | None = None,
    ) -> Iterator[None]:
        """Attribute every file that appears under *root* inside the block.

        Args:
            root: Staging directory a framework generator writes into.
            node_id: Node to credit for whatever appears.
            verb: Generator verb being invoked.
            module: Bounded-context slug, when applicable.
            rebase: Project-relative directory the staged files will be
                copied to. Recorded paths are ``<rebase>/<name>`` so the
                ledger speaks in final project paths, not staging paths.
        """
        before = _snapshot(root)
        try:
            yield
        finally:
            for relative in sorted(_snapshot(root) - before):
                path = f"{rebase}/{relative}" if rebase else relative
                self.record(path, node_id=node_id, verb=verb, module=module)

    def record_for(self, path: str) -> EmittedFile | None:
        """The attribution recorded for *path*, or None if nothing claims it.

        Returns the record rather than one of its fields because callers
        want different parts of it -- the canvas wants the node, the console
        wants the module -- and widening a tuple every time is how a
        progress callback grows five positional arguments.
        """
        norm = path.replace("\\", "/")
        for record in self._records:
            if record.path == norm:
                return record
        return None

    def node_for(self, path: str) -> str | None:
        """Node that caused *path* to exist, or None if nothing claims it.

        The inverse of :meth:`files_by_node`, for callers that learn about
        files one at a time -- progress streams, mainly. Attribution is
        looked up rather than re-derived from the path, which is the whole
        point of the ledger: a consumer that pattern-matched
        ``src/app/models/...`` would have to be taught every structure and
        would go quietly wrong under modular.
        """
        record = self.record_for(path)
        return record.node_id if record else None

    def files_by_node(self) -> dict[str, list[str]]:
        """Fold to the ``{node_id: [paths]}`` shape the UI persists.

        Unattributed files are dropped, matching the previous behavior:
        the canvas can only light up nodes that exist.
        """
        tally: dict[str, set[str]] = {}
        for record in self._records:
            if record.node_id is None:
                continue
            tally.setdefault(record.node_id, set()).add(record.path)
        return {node: sorted(paths) for node, paths in sorted(tally.items())}


def _snapshot(root: Path) -> set[str]:
    if not root.exists():
        return set()
    return {
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file()
    }
