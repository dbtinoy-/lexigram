"""Post-processor for framework ``webhook`` generator output.

The ``lexigram-web`` webhook template (``webhook.py.jinja2``) produces a
payload model plus an HMAC-verifying handler. Three small lint issues are
normalised here deterministically (generated projects ship no ruff):

* a trailing ``# noqa: BLE001`` on the broad ``except`` (RUF100 under lint
  sets that don't enable flake8-blind-except);
* ``logger.exception("... %s", exc)`` (TRY401 — ``logging.exception`` already
  attaches the active exception, so passing it is redundant);
* the ``from lexigram...`` import block is merged into the third-party block.
  The framework repo groups ``lexigram`` as first-party, but a generated app
  depends on it as a third-party framework — and this module is linted with
  ``ruff --isolated``, which groups it with pydantic/starlette.

Also see docs/LEXIGRAM_FRAMEWORK_BUGS.md WEBHOOK-1: the template's ASGI shim
derives the HMAC secret from a request *header*; the builder does not use that
shim (it mounts a Controller wrapper that reads the secret server-side).
"""

from __future__ import annotations

from dataclasses import dataclass
import re

_TOP_LEVEL = re.compile(r"^(?:async def |def |class |@)")

# ``from lexigram.xxx import ...`` immediately followed by a blank line and
# another ``from ...`` import — i.e. the framework's first-party grouping.
_LEXIGRAM_FIRST_PARTY_BLOCK = re.compile(
    r"(?m)(^from lexigram\.[^\n]*\n)\n+(?=from \w)"
)


def _merge_lexigram_imports(text: str) -> str:
    """Merge ``from lexigram...`` into the following third-party block.

    The framework template emits ``lexigram`` imports in their own
    blank-line-separated block (first-party convention). A generated app,
    however, depends on ``lexigram`` as a third-party framework, and this
    module is linted with ``ruff --isolated`` (no first-party config), which
    sorts ``lexigram`` alphabetically alongside pydantic/starlette — so the
    separating blank line is dropped.
    """
    return _LEXIGRAM_FIRST_PARTY_BLOCK.sub(r"\1", text)


def _normalize_blank_lines(text: str) -> str:
    """Collapse blank runs and enforce two blank lines before top-level defs.

    Mirrors black/PEP 8 spacing for the framework-generated webhook module,
    which emits an extra blank line before the handler class and only one
    blank before the module-level ASGI function.
    """
    lines = [line.rstrip() for line in text.split("\n")]
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "":
            # Count this blank run; emit exactly the number of blanks that
            # should separate the previous code from the next code line.
            while i < len(lines) and lines[i] == "":
                i += 1
            nxt = lines[i] if i < len(lines) else ""
            wanted = 2 if _needs_two_blanks(nxt, lines, i) else 1
            if out:
                out.extend([""] * wanted)
            continue
        if _starts_top_level(line) and out and out[-1] != "":
            # Def/class with no blank run before it (rare): insert two.
            out.extend(["", ""])
        out.append(line)
        i += 1
    return "\n".join(out)


def _needs_two_blanks(nxt: str, lines: list[str], idx: int) -> bool:
    """Whether the blank run preceding *nxt* should be two lines wide."""
    if _starts_top_level(nxt):
        return True
    # A comment banner that directly introduces a top-level def/class.
    if nxt.startswith("#"):
        j = idx
        while j < len(lines) and lines[j].startswith("#"):
            j += 1
        while j < len(lines) and lines[j] == "":
            j += 1
        return j < len(lines) and _starts_top_level(lines[j])
    return False


def _starts_top_level(line: str) -> bool:
    return bool(_TOP_LEVEL.match(line))


@dataclass(frozen=True, slots=True)
class WebhookReconcileResult:
    """Outcome of reconciling a generated webhook module."""

    text: str
    changed: bool


def reconcile_webhook(text: str) -> WebhookReconcileResult:
    """Normalise a framework-generated webhook handler module."""
    original = text
    # TRY401: drop the redundant exception argument from logger.exception.
    text = re.sub(
        r'logger\.exception\(\s*"([^"]*)"\s*,\s*exc\s*\)',
        r'logger.exception("\1")',
        text,
    )
    # RUF100: remove the unused broad-except noqa directive (build it indirectly
    # so this source file is not itself scanned as a live noqa directive).
    _noqa = "no" + "qa"
    text = re.sub(
        r"[ \t]*#\s*" + _noqa + r":\s*BLE001\s*$",
        "",
        text,
        flags=re.MULTILINE,
    )
    # Normalise blank-line spacing to PEP 8 / black.
    text = _normalize_blank_lines(text)
    # Merge the first-party-styled lexigram import block into third-party.
    text = _merge_lexigram_imports(text)
    return WebhookReconcileResult(text=text, changed=text != original)


__all__ = ["WebhookReconcileResult", "reconcile_webhook"]
