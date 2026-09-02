"""Delete generated files the graph no longer produces.

The managed roots are derived from the verb table through the layout rather
than listed, so adding a component kind or changing a structure cannot leave
an unpruned directory behind.
"""

from __future__ import annotations

from pathlib import Path

from lexigram.builder.gen.layout import DEFAULT_LAYOUT, WriterLayout
from lexigram.builder.gen.node_generators import VERB_SPECS, dest_for

__all__ = ["prune_stale_generated"]


def prune_stale_generated(
    project_dir: Path, *, keep: set[str], layout: WriterLayout | None = None
) -> None:
    """Delete previously generated files that are no longer produced.

    Managed roots are derived from the verb table through *layout*, so a
    structure change can never leave an unpruned directory behind. Builder-
    owned packages with no generator verb are listed explicitly.
    """
    active = layout or DEFAULT_LAYOUT
    # Both shapes are pruned every time, because both can exist in one
    # project: unscoped components sit at the app root while scoped ones sit
    # under `modules/`, and a node that moves between them leaves a file
    # behind in whichever tree it left.
    managed_roots = [
        *_app_root_managed_roots(project_dir, active),
        project_dir / "src" / active.app_package / "modules",
        project_dir / "src" / active.app_package / "shared",
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


def _app_root_managed_roots(project_dir: Path, active: WriterLayout) -> list[Path]:
    """Managed roots for the single-package structures."""
    return [
        project_dir / Path(dest_for(verb, active))
        for verb in sorted(VERB_SPECS)
        if verb != "resource"
    ] + [
        project_dir / Path(active.app_path("auth")),
        project_dir / Path(active.app_path("emails")),
        project_dir / Path(active.app_path("validators")),
        project_dir / Path(active.app_path("uploads")),
        project_dir / Path(active.app_path("contracts")),
        project_dir / Path(active.app_path("di")),
        project_dir / "migrations" / "versions",
        project_dir / "tests",
    ]
