"""Deterministic post-processing for the framework ``graphql`` generator.

The lexigram-graphql ``graphql`` generator renders a Strawberry schema module
with two framework template defects that must be repaired before the file is
committed to a lint-clean project:

* The list-resolver body contains a bare ``orders # TODO: Implement ...``
  statement. ``orders`` is undefined in that scope, so Strawberry executes the
  resolver at schema-construction time and raises ``NameError`` (ruff F821).
* Several rendered imports are unused / import from the wrong module
  (``AsyncIterator`` from ``typing`` instead of ``collections.abc``), and the
  template leaves runs of >2 blank lines.

These are framework bugs (documented in ``docs/LEXIGRAM_FRAMEWORK_BUGS.md``);
we repair the *generated output* here rather than patching the submodule.
``reconcile_graphql`` returns a :class:`ReconcileResult` mirroring the other
emitters so the writer can surface diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

# A bare ``<word> # TODO: Implement ...`` line is an undefined-name stub left
# by the list resolver template. Drop the statement but keep the TODO note.
_BARE_TODO_RESOLVER = re.compile(
    r"^[ \t]*[A-Za-z_][A-Za-z0-9_]*\s+#\s*TODO:[^\n]*$\n?",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    """Result of reconciling a generated file."""

    text: str
    changed: bool = True


def reconcile_graphql(text: str) -> ReconcileResult:
    """Repair the framework GraphQL template's lint/runtime defects."""
    original = text

    # 1. Remove the bare undefined-name stub in the list resolver.
    text = _BARE_TODO_RESOLVER.sub("", text)

    # 2. Import AsyncIterator from collections.abc (ruff UP035) and drop the
    #    unused UTC import the template always emits.
    text = text.replace(
        "from datetime import UTC, datetime",
        "from datetime import datetime",
    )
    text = text.replace(
        "from typing import Any, AsyncIterator, List, Optional",
        "from collections.abc import AsyncIterator\nfrom typing import List, Optional",
    )
    # ``Any`` is only referenced in comments; remove if now unused.
    if not re.search(r"(?<![\w.])Any(?![\w])", text.split("import strawberry", 1)[-1]):
        text = text.replace(
            "from typing import Any, List, Optional",
            "from typing import List, Optional",
        )

    # 3. Collapse runs of 3+ blank lines (and stray whitespace-only lines) down
    #    to a single blank line, then normalise >2 consecutive newlines.
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.rstrip("\n") + "\n"

    return ReconcileResult(text=text, changed=text != original)
