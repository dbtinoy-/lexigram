"""Runtime helpers for optional dependencies."""

from __future__ import annotations

from lexigram.ai.rag.deps.optional import (
    MissingOptionalDependencyError,
    ensure_packages,
)

__all__ = ["MissingOptionalDependencyError", "ensure_packages"]
