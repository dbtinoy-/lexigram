"""Bridge to framework CLI generators via the contribution system.

Resolves generator definitions through ``lexigram.cli.contributors``
entry points (the exact discovery the lexigram-cli ``CommandAssembler``
uses: ``populate_cli_registries`` → ``contributor.get_generators()`` →
``GeneratorDefinition.generator_path`` ``"module:Class"``), so the builder
always exercises the packages' own generators — never a parallel copy.

The CLI invokes a generator as::

    adapter.generate(name, output_dir=..., fields_str=..., dry_run=..., force=...)

i.e. ``output_dir`` is passed to the generator (it re-points
``self.output_dir``) while ``dry_run``/``force``/extra kwargs flow through
``resolve_options(**options)``. We mirror that contract here.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import importlib
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from lexigram.logging import get_logger

from lexigram.builder.exceptions import GenerationError

_logger = get_logger(__name__)

ENTRY_POINT_GROUP = "lexigram.cli.contributors"

__all__ = [
    "ContributorGenerator",
    "available_generators",
    "discover_generators",
    "load_generator",
]


@dataclass(frozen=True, slots=True)
class ContributorGenerator:
    """A lazily-loaded generator class plus its contributor metadata."""

    contributor: str
    name: str
    cls: type


@lru_cache(maxsize=1)
def discover_generators() -> dict[str, ContributorGenerator]:
    """Map generator verb-name -> contributor generator across packages.

    Discovery is cached (entry-point scanning is repeated per entity today).
    A broken contributor is skipped with a warning — matching the CLI's
    behavior of aggregating load errors rather than aborting the whole
    generator surface.
    """
    out: dict[str, ContributorGenerator] = {}
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            module = importlib.import_module(ep.module)
            contributor_cls = getattr(module, ep.attr)
            contributor = contributor_cls()
            for definition in contributor.get_generators():
                module_path, _, class_name = definition.generator_path.partition(":")
                try:
                    gcls = getattr(importlib.import_module(module_path), class_name)
                except (ImportError, AttributeError) as exc:
                    _logger.warning(
                        "generator_class_unresolvable",
                        contributor=ep.name,
                        generator=definition.name,
                        path=definition.generator_path,
                        error=str(exc),
                    )
                    continue
                out[definition.name] = ContributorGenerator(
                    contributor=definition.contributor,
                    name=definition.name,
                    cls=gcls,
                )
        except Exception as exc:  # noqa: BLE001 - skip broken contributors
            _logger.warning(
                "cli_contributor_skipped", contributor=ep.name, error=str(exc)
            )
            continue
    return dict(out)


def available_generators() -> tuple[str, ...]:
    """Return the sorted names of every resolvable framework generator."""
    return tuple(sorted(discover_generators()))


def load_generator(verb: str, *, output_dir: Path) -> Any:
    """Instantiate the contributed generator for *verb* at *output_dir*.

    Mirrors lexigram-cli's ``GeneratorAdapter``: the generator is
    constructed with ``output_dir`` when its signature accepts it,
    otherwise with no arguments.

    Raises:
        GenerationError: If no contributor registers *verb*, with a message
            listing the generators that *are* available.
    """
    gen = discover_generators().get(verb)
    if gen is None:
        available = ", ".join(available_generators()) or "(none discovered)"
        raise GenerationError(
            f"no CLI contributor registers generator {verb!r}; "
            f"available generators: {available}"
        )
    try:
        return gen.cls(output_dir=output_dir)
    except TypeError:
        # Generators with a fixed/no-arg constructor (Adapter-style fallback).
        return gen.cls()
