"""Deterministic post-processing for the lexigram-events ``event`` generator.

The event generator renders a frozen ``DomainEvent`` dataclass with a
``build_<event>`` helper, but the template has two defects:

* Field type names are rendered verbatim from the field-spec string, so a
  ``uuid`` field is annotated as ``order_id: uuid`` — an undefined name
  (ruff F821; ``uuid`` lowercase is the module, not a type). The file already
  imports ``UUID`` from ``uuid``.
* It leaves runs of >2 blank lines.

The template itself is valid Python (trailing commas on the ``build_*()``
signature are fine); the only repair needed on *our* side is mapping the raw
``uuid`` token to the imported ``UUID`` and collapsing blank lines. The
result is then passed through ``ruff check --fix`` (``ruff_autofix=True`` on
the VerbSpec).
"""

from __future__ import annotations

from dataclasses import dataclass
import re

# Map a raw field-spec type token to a valid Python annotation that is either
# a builtin or already imported in the event template (UUID is imported).
_FIELD_TYPE_FIXES: dict[str, str] = {
    "uuid": "UUID",
}

# Annotation of the form ``    <name>: <type>`` — in both the frozen
# dataclass body and the ``build_<event>()`` signature. The signature form
# carries a trailing comma (and, for optional fields, `` | None = None``),
# so everything after the first type token is preserved verbatim (group 3)
# while only that first token (group 2) is rewritten.
_ANNOTATION = re.compile(r"^(\s{4}[A-Za-z_]\w*:\s*)([A-Za-z_][\w.]*)(.*)$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    """Result of reconciling a generated file."""

    text: str
    changed: bool = True


def reconcile_event(text: str) -> ReconcileResult:
    """Repair the event template's undefined-type annotation and blank lines."""
    original = text

    def _fix_annotation(match: re.Match[str]) -> str:
        prefix, type_token, suffix = match.group(1), match.group(2), match.group(3)
        fixed = _FIELD_TYPE_FIXES.get(type_token, type_token)
        return f"{prefix}{fixed}{suffix}"

    text = _ANNOTATION.sub(_fix_annotation, text)

    # Collapse runs of 3+ blank lines down to a single blank line.
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.rstrip("\n") + "\n"

    return ReconcileResult(text=text, changed=text != original)
