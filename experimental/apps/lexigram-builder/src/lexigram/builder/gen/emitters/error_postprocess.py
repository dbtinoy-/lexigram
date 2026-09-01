"""Post-processing for generated web HTTP-error modules.

The framework lexigram-web ``error`` generator runs the module docstring
straight into the first import (no separating blank line), which
``ruff format`` wants after the docstring. We insert the blank line
deterministically so the module is format-clean regardless of whether ruff
is available at generation time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ErrorReconcileResult:
    """Outcome of reconciling a generated error module."""

    text: str


def reconcile_error(text: str) -> ErrorReconcileResult:
    """Normalise a generated HTTP-error module to a format-clean form.

    Args:
        text: The generated error module source.

    Returns:
        An :class:`ErrorReconcileResult` with the reconciled source.
    """
    # Insert a blank line between the module docstring and the first import
    # when the template omits it (closing ``"""`` immediately followed by
    # ``from __future__``).
    text = text.replace(
        'domain.\n"""\nfrom __future__',
        'domain.\n"""\n\nfrom __future__',
    )
    return ErrorReconcileResult(text=text)
