"""Deterministic post-processing for the framework ``health`` generator.

The lexigram-monitor ``health_check`` generator names the check class after
the (snake_case) entity without converting it to PascalCase — it renders
``class order(HealthCheck):``. A lowercase class name violates PEP 8 naming
(ruff N801) and is not idiomatic. The framework template also passes
``critical`` to ``HealthCheck.__init__``; we leave that as generated.

This is a framework bug (documented in ``docs/LEXIGRAM_FRAMEWORK_BUGS.md``);
we repair the *generated output* here rather than patching the submodule.
``reconcile_health`` returns a :class:`ReconcileResult` mirroring the other
emitters.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from lexigram.contracts.cli.generators import pascal_case


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    """Result of reconciling a generated file."""

    text: str
    changed: bool = True


def reconcile_health(text: str, pascal: str = "", critical: bool = True) -> ReconcileResult:
    """Rewrite the generated health check to an idiomatic PascalCase class.

    Args:
        text: Raw generated module text.
        pascal: PascalCase class stem (e.g. ``Order``). When empty it is
            derived from the ``class <snake>(HealthCheck)`` declaration.
        critical: Whether the check is critical (unused for the rename but
            kept for signature symmetry with future fields).
    """
    del critical
    original = text

    match = re.search(r"^class\s+([A-Za-z_]\w*)\s*\(\s*HealthCheck\s*\)\s*:", text, re.MULTILINE)
    snake = match.group(1) if match else ""
    cls_name = pascal or (pascal_case(snake) if snake else "HealthCheck")

    if match and snake != cls_name:
        # Rename the class declaration.
        text = text[: match.start(1)] + cls_name + text[match.end(1) :]

    return ReconcileResult(text=text, changed=text != original)
