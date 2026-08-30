"""Node generators — VerbSpec entries mapping node kinds to framework generators.

Each ``VerbSpec`` describes how a node kind maps to a CLI generator name,
the package that owns it, and the output directory inside the generated
project.  ``ENTITY_ATTACHED`` entries handle entity-driven generation
(e.g. a service wired to an entity).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram_builder.graph.palette import (
    KIND_AUTH,
    KIND_CONTRACT,
    KIND_ENTITY,
    KIND_FEATURE_FLAG,
    KIND_JOB,
    KIND_RATE_LIMIT,
    KIND_ROLE,
    KIND_ROUTE,
    KIND_SERVICE,
)


@dataclass(frozen=True, slots=True)
class VerbSpec:
    """Maps a node kind to a framework generator invocation.

    Attributes:
        kind: The node kind string.
        generator_name: The CLI generator name (e.g. ``"feature_flag"``).
        package: The framework package that owns the generator.
        output_dir: Output directory inside the generated project.
    """

    kind: str
    generator_name: str
    package: str
    output_dir: str


# ── Verb specs ────────────────────────────────────────────────────────

VERB_SPECS: tuple[VerbSpec, ...] = (
    VerbSpec(
        kind=KIND_FEATURE_FLAG,
        generator_name="feature_flag",
        package="features",
        output_dir="src/app/features",
    ),
    VerbSpec(
        kind=KIND_AUTH,
        generator_name="auth_guard",
        package="auth",
        output_dir="src/app/guards",
    ),
    VerbSpec(
        kind=KIND_ROLE,
        generator_name="guard",
        package="auth",
        output_dir="src/app/guards",
    ),
    VerbSpec(
        kind=KIND_RATE_LIMIT,
        generator_name="rate_limit",
        package="auth",
        output_dir="src/app/guards",
    ),
    VerbSpec(
        kind=KIND_CONTRACT,
        generator_name="contract",
        package="web",
        output_dir="src/app/contracts",
    ),
    VerbSpec(
        kind=KIND_ENTITY,
        generator_name="model",
        package="sql",
        output_dir="src/app/models",
    ),
    VerbSpec(
        kind=KIND_SERVICE,
        generator_name="service",
        package="core",
        output_dir="src/app/services",
    ),
    VerbSpec(
        kind=KIND_JOB,
        generator_name="job",
        package="tasks",
        output_dir="src/app/jobs",
    ),
    VerbSpec(
        kind=KIND_ROUTE,
        generator_name="resource",
        package="web",
        output_dir="src/app/controllers",
    ),
)

# Index for O(1) lookup by kind.
_VERB_SPECS_BY_KIND: dict[str, VerbSpec] = {spec.kind: spec for spec in VERB_SPECS}


def get_verb_spec(kind: str) -> VerbSpec | None:
    """Look up the VerbSpec for a node kind."""
    return _VERB_SPECS_BY_KIND.get(kind)


# ── Entity-attached generation ────────────────────────────────────────
# Some nodes are driven by an ``entity -> <node>`` edge and need extra
# kwargs derived from the entity config.

ENTITY_ATTACHED: frozenset[str] = frozenset(
    {
        KIND_SERVICE,
        KIND_JOB,
    }
)


def entity_attached_extra_kwargs(
    kind: str,
    entity_name: str,
    entity_fields: str,
) -> dict[str, Any]:
    """Return extra generator kwargs for entity-attached nodes.

    Args:
        kind: The node kind.
        entity_name: The entity's snake_case name.
        entity_fields: The entity's field spec string.

    Returns:
        A dict of extra kwargs to pass to the generator.
    """
    if kind == KIND_SERVICE:
        return {"entity": entity_name, "fields": entity_fields}
    if kind == KIND_JOB:
        return {"entity": entity_name}
    return {}


__all__ = [
    "ENTITY_ATTACHED",
    "VERB_SPECS",
    "VerbSpec",
    "entity_attached_extra_kwargs",
    "get_verb_spec",
]
