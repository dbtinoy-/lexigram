"""Post-processing for generated SQL seeder modules.

The framework lexigram-sql ``seeder`` generator emits timestamps with
``datetime.now(timezone.utc)`` (the deprecated spelling under modern
``datetime`` rules; ruff UP017 prefers the ``datetime.UTC`` alias) and an
import block that normalises differently across generator versions. We
rewrite both so the module is lint-clean deterministically, without relying
on ruff being available at generation time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SeederReconcileResult:
    """Outcome of reconciling a generated seeder module."""

    text: str


def reconcile_seeder(text: str) -> SeederReconcileResult:
    """Normalise a generated seeder module to a lint-clean form.

    Args:
        text: The generated seeder module source.

    Returns:
        A :class:`SeederReconcileResult` with the reconciled source.
    """
    # UP017: prefer the ``datetime.UTC`` alias over ``timezone.utc``.
    text = text.replace(
        "from datetime import datetime, timezone",
        "from datetime import UTC, datetime",
    )
    text = text.replace("datetime.now(timezone.utc)", "datetime.now(UTC)")
    # isort: the template leaves a double blank line between the import block
    # and ``SEED_DATA``; collapse to a single blank so the import section ends
    # cleanly (ruff format re-applies PEP 8 two-blank spacing elsewhere).
    text = text.replace(
        "from lexigram.sql import SimpleUnitOfWork\n\n\nSEED_DATA",
        "from lexigram.sql import SimpleUnitOfWork\n\nSEED_DATA",
    )
    return SeederReconcileResult(text=text)
