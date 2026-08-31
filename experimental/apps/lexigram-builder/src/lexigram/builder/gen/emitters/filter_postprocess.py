"""Post-processing for generated web exception-filter modules.

The framework lexigram-web ``exception_filter`` generator runs the module
docstring straight into the first import (no separating blank line), which
``ruff format`` wants after the docstring. We insert the blank line
deterministically so the module is format-clean regardless of whether ruff
is available at generation time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FilterReconcileResult:
    """Outcome of reconciling a generated exception-filter module."""

    text: str


def reconcile_exception_filter(text: str) -> FilterReconcileResult:
    """Normalise a generated exception-filter module to a format-clean form.

    Args:
        text: The generated exception-filter module source.

    Returns:
        A :class:`FilterReconcileResult` with the reconciled source.
    """
    # Insert a blank line between the module docstring and the first import
    # when the template omits it (the closing ``"""`` is immediately followed
    # by ``from __future__``).
    text = text.replace(
        'JSON response.\n"""\nfrom __future__',
        'JSON response.\n"""\n\nfrom __future__',
    )
    return FilterReconcileResult(text=text)
