"""Audit write-hook injection for reconciled controllers (nodes plan N4.1).

The framework has no audit decorator or observer hook, so the builder
injects the calls themselves — same builder-side pattern as the flag gates
and the guard chain:

- Entities wired to an enabled ``audit_log`` node get an ``<Entity>AuditRepository``
  DI parameter appended to the controller constructor (``audit``) plus the
  repository import.
- Wired ``create`` / ``update`` / ``delete`` handlers record one audit row
  just before their final success ``return`` (after the mutation and the
  not-found check succeeded — failures are never audited). The controller
  stays a one-liner per op; redaction/capture lives in the repository.
- Degradation is no-injection: a handler whose shape does not match the
  framework template (no final 8-space ``return``) is returned unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

_HANDLER_DEF = re.compile(
    r"^(?P<indent>[ ]{4})async def (?P<op>create|get|list|update|delete)\(",
    re.MULTILINE,
)
_CONTROLLER_IMPORT_LINE = re.compile(
    r"^from lexigram\.web import Controller.*$", re.MULTILINE
)
_CTOR_DEF = re.compile(
    r"^    def __init__\(self, (?P<params>[^()]*)\) -> None:$",
    re.MULTILINE,
)
_SUPER_LINE = "        super().__init__()"
_FINAL_RETURN = re.compile(r"^        return\b")
_MARKER = "self._audit.record_"


@dataclass(frozen=True, slots=True)
class ControllerAuditHooks:
    """Audit wiring for one entity's controller.

    Attributes:
        ops: CRUD ops that record audit rows (subset of create/update/delete).
        repo_class: The audit repository class to inject (e.g.
            ``NoteAuditRepository``).
        repo_module: Module path for the import (e.g.
            ``app.repositories.note_audit_repository``).
    """

    ops: frozenset[str]
    repo_class: str
    repo_module: str

    @property
    def wired(self) -> bool:
        return bool(self.ops)


def apply_audit(text: str, hooks: ControllerAuditHooks) -> str:
    """Inject the audit repository DI + write hooks into a controller."""
    if not hooks.wired:
        return text
    if _MARKER in text:
        return text  # idempotent: already audited

    text = _ensure_audit_import(text, hooks)
    text = _inject_audit_dependency(text, hooks)

    out: list[str] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        match = _HANDLER_DEF.match(line)
        if match is None:
            out.append(line)
            i += 1
            continue
        op = match.group("op")
        body_start = _handler_body_start(lines, i)
        body_end = _handler_body_end(lines, body_start)
        body = "\n".join(lines[body_start:body_end])
        out.extend(lines[i:body_start])
        if op in hooks.ops and _MARKER not in body:
            insertion = _audit_insertion_lines(op, body)
            if insertion is not None:
                ret_index = _final_return_index(lines, body_start, body_end)
                if ret_index is not None:
                    out.extend(lines[body_start:ret_index])
                    out.extend(insertion)
                    out.extend(lines[ret_index:body_end])
                    i = body_end
                    continue
        out.extend(lines[body_start:body_end])
        i = body_end
    return "\n".join(out)


def _audit_insertion_lines(
    op: str, body: str
) -> list[str] | None:
    """The audit call(s) to splice in before the handler's final return.

    ``None`` when the handler body does not expose the expected row
    variable (template drift) — the hook degrades to no-injection.
    """
    if op == "create":
        if "created = await self.repo.create(" not in body:
            return None
        return [
            "        _audit_row = _to_dict(created)",
            '        await self._audit.record_created(',
            '            str(_audit_row.get("id", "")), _audit_row,',
            "        )",
        ]
    if op == "update":
        if "updated = await self.repo.update(" not in body:
            return None
        return [
            "        _audit_row = _to_dict(updated)",
            "        await self._audit.record_updated(",
            '            str(_audit_row.get("id", "")), _audit_row,',
            "        )",
        ]
    if op == "delete":
        if "await self.repo.delete(" not in body:
            return None
        return ["        await self._audit.record_deleted(item_id)"]
    return None  # get/list are never audited


def _final_return_index(
    lines: list[str], body_start: int, body_end: int
) -> int | None:
    """Index of the last top-level (8-space) ``return`` in the handler body."""
    index: int | None = None
    for j in range(body_start, body_end):
        if _FINAL_RETURN.match(lines[j]):
            index = j
    return index


def _handler_body_end(lines: list[str], body_start: int) -> int:
    """Index one past the last line of the handler.

    The handler body is every blank line / line indented deeper than the
    ``async def`` (>= 8 spaces). The first non-blank line at a shallower
    indent (next decorator, next method, module-level def, EOF) ends it —
    this keeps module-level helpers that follow the class out of the scan
    window.
    """
    j = body_start
    while j < len(lines):
        line = lines[j]
        if line.strip() and not line.startswith("        "):
            return j
        j += 1
    return j


def _handler_body_start(lines: list[str], def_index: int) -> int:
    """Index of the first statement line of the handler body.

    Skips the (possibly multi-line) signature, then the docstring when the
    body opens with one (same semantics as flag_postprocess).
    """
    j = def_index
    while j < len(lines) and not lines[j].rstrip().endswith(":"):
        j += 1
    j += 1  # first body line
    # Skip a docstring, if present.
    if j < len(lines):
        stripped = lines[j].lstrip()
        if stripped.startswith('"""'):
            if stripped.endswith('"""') and len(stripped) > 3:
                return j + 1  # single-line docstring
            j += 1
            while j < len(lines) and '"""' not in lines[j]:
                j += 1
            return j + 1
    return j


def _ensure_audit_import(text: str, hooks: ControllerAuditHooks) -> str:
    if f"import {hooks.repo_class}" in text:
        return text  # already imported (idempotency probe)
    inline = f"from {hooks.repo_module} import {hooks.repo_class}"
    if len(inline) <= 88:
        import_line = inline
    else:  # ruff-format style parenthesized import
        import_line = (
            f"from {hooks.repo_module} import (\n    {hooks.repo_class},\n)"
        )
    match = _CONTROLLER_IMPORT_LINE.search(text)
    if match is None:
        return text.replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\n\n" + import_line,
            1,
        )
    end = match.end()
    return text[:end] + "\n" + import_line + text[end:]


def _inject_audit_dependency(
    text: str, hooks: ControllerAuditHooks
) -> str:
    """Append the audit repository to the controller constructor.

    When the controller has no recognizable constructor (code-preview
    stubs), a minimal one is synthesized before the first handler so the
    previewed source stays self-consistent.
    """
    lines = text.split("\n")
    ctor_index: int | None = None
    for i, line in enumerate(lines):
        if _CTOR_DEF.match(line):
            ctor_index = i
            break
    if ctor_index is None:
        return _synthesize_ctor(text, hooks)

    params = _CTOR_DEF.match(lines[ctor_index]).group("params").strip()  # type: ignore[union-attr]
    sep = f"{params}, " if params else ""
    inline = f"    def __init__(self, {sep}audit: {hooks.repo_class}) -> None:"
    if len(inline) <= 88:
        lines[ctor_index] = inline
    else:
        # Wrap one-param-per-line (ruff-format style) — the controller verb
        # is not ruff-autofixed, so long signature lines are wrapped here.
        param_lines = [p.strip() for p in sep.split(",") if p.strip()]
        param_lines.append(f"audit: {hooks.repo_class}")
        lines[ctor_index] = "    def __init__(\n" + "\n".join(
            f"        {p}," for p in param_lines
        ) + "\n    ) -> None:"

    # Insert the assignment after the ctor's last 8-indented statement
    # (immediately after super().__init__() when it is the only one).
    j = ctor_index + 1
    last_stmt = j
    while j < len(lines) and lines[j].startswith("        "):
        j += 1
        last_stmt = j
    lines.insert(last_stmt, "        self._audit = audit")
    return "\n".join(lines)


def _synthesize_ctor(text: str, hooks: ControllerAuditHooks) -> str:
    """Insert a minimal audit-only constructor before the first handler."""
    lines = text.split("\n")
    insert_at: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("    @") or line.startswith("    async def "):
            insert_at = i
            break
    if insert_at is None:
        return text  # no handler anchor — degrade to no-injection
    ctor = [
        f"    def __init__(self, audit: {hooks.repo_class}) -> None:",
        "        super().__init__()",
        "        self._audit = audit",
        "",
    ]
    lines[insert_at:insert_at] = ctor
    return "\n".join(lines)
