"""Modular-structure code generation.

Orchestration for the ``modular`` structure lives here rather than growing
``writer.py`` (roadmap G8). Everything in this package is a pure function
from the graph to file contents; committing them is the writer's job.
"""

from __future__ import annotations

from lexigram.builder.gen.modular.composition import (
    asgi_target,
    emit_app,
    feature_set,
)
from lexigram.builder.gen.modular.orchestration import (
    commit_staged,
    emit_modular_project,
)
from lexigram.builder.gen.modular.placement import Placement, sole
from lexigram.builder.gen.modular.providers import (
    RepositoryBinding,
    emit_infrastructure,
    emit_persistence_provider,
    framework_modules,
    repository_bindings,
)

__all__ = [
    "Placement",
    "RepositoryBinding",
    "asgi_target",
    "commit_staged",
    "emit_app",
    "emit_infrastructure",
    "emit_modular_project",
    "emit_persistence_provider",
    "feature_set",
    "framework_modules",
    "repository_bindings",
    "sole",
]
