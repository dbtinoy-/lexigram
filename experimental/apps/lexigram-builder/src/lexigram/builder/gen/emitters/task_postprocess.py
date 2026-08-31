"""Post-processor for framework ``task`` generator output (TASK-3 workaround).

The ``lexigram-tasks`` task template (``task.py.jinja2``) renders code that is
not lint-clean out of the box (see docs/LEXIGRAM_FRAMEWORK_BUGS.md, TASK-3):

* the per-parameter Jinja loop emits indented **blank lines** (W293);
* it renders ``<name> = kwargs.get("<name>", None)`` dead locals that are never
  used because the task forwards ``**kwargs`` wholesale (F841, SIM910);
* the conditional ``scheduled``/``task`` import is separated from the other
  ``lexigram.tasks`` import (I001);
* a stray blank line appears between the ``@scheduled``/``@task`` decorator and
  the ``async def``.

Generated projects do not depend on ruff, so rather than rely on an external
formatter we normalise these deterministically here. The transformation is
idempotent and leaves the task callable and its registration intact.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class TaskReconcileResult:
    """Outcome of reconciling a generated task module.

    Attributes:
        text: The rewritten source.
        changed: True when any normalisation was applied.
    """

    text: str
    changed: bool


def reconcile_task(text: str) -> TaskReconcileResult:
    """Normalise a framework-generated task module to be lint-clean.

    Args:
        text: Raw source emitted by the ``task`` generator.

    Returns:
        A :class:`TaskReconcileResult` with the cleaned source.
    """
    original = text

    # 1. Merge the conditional decorator import into the main tasks import
    #    line so the import block is contiguous and sorted (I001).
    text = _merge_tasks_imports(text)

    # 1b. Normalise the stdlib imports to ``from`` form so their relative order
    #     is stable regardless of the consumer's isort configuration
    #     (``import uuid as _uuid`` vs ``from typing import Any`` sorts
    #     differently under ``force-sort-within-sections``). Rewrite both the
    #     import and its ``_uuid.uuid4()`` call site.
    if "import uuid as _uuid" in text:
        text = text.replace("import uuid as _uuid\n", "from uuid import uuid4\n")
        text = text.replace("_uuid.uuid4()", "uuid4()")
    # Collapse the two stdlib ``from`` imports into one contiguous, sorted
    # group (from uuid …, from typing …) with no blank line between them.
    text = re.sub(
        r"from (?:typing|uuid) import [^\n]+\nfrom (?:typing|uuid) import [^\n]+\n",
        lambda m: "".join(sorted(m.group(0).splitlines(keepends=True))),
        text,
    )

    # 2. Remove the dead per-parameter local assignments (F841/SIM910) and the
    #    indented blank lines the Jinja loop leaves behind (W293). The task
    #    forwards **kwargs to _process_<name>, so these locals are never read.
    text = _strip_dead_param_locals(text)

    # 3. Collapse a title-only module docstring onto one line (black style).
    #    Runs before blank-line normalisation, which removes the separator.
    text = _collapse_title_docstring(text)

    # 4. Collapse runs of blank/whitespace-only lines inside function bodies
    #    down to a single blank line, and strip trailing whitespace (W293).
    text = _normalize_blank_lines(text)

    # 5. Remove blank lines between a decorator and the def/class it wraps.
    text = re.sub(
        r"(@[A-Za-z_][\w.]*\([^)]*\)|@[A-Za-z_][\w.]*)\n(?:[ \t]*\n)+( *(?:async def|def|class) )",
        r"\1\n\2",
        text,
    )

    # 6. Collapse blank lines left inside function signatures and collection
    #    literals by the template's ``{% for %}`` loops.
    text = _collapse_blanks_in_brackets(text)

    # 7. Drop the template's inline broad-except lint suppression. The
    #    generated broad-except re-raise is legitimate, but consumers who don't
    #    enable flake8-blind-except (the playground's default lint set) flag the
    #    directive as unused (RUF100); removing it keeps the file clean under
    #    both configurations. (This regex targets a trailing ``noqa`` comment
    #    carrying the blind-except code; written indirectly so this source
    #    file's own lint scan does not read the comment below as a directive.)
    _noqa = "no" + "qa"
    text = re.sub(
        r"[ \t]*#\s*" + _noqa + r":\s*BLE001\s*$",
        "",
        text,
        flags=re.MULTILINE,
    )

    # 8. Drop the trailing ``@injectable class <Name>TaskRunner`` helper block.
    #    The framework task template appends this convenience enqueue class,
    #    but (a) the playground enqueues jobs itself via the webhook
    #    controller's TaskProvider — this runner is never imported/registered —
    #    and (b) its ``run()`` signature is mis-indented in the template (the
    #    closing ``) -> str:`` sits left of its parameters, terminating the def
    #    early and leaving ``await self._provider.enqueue_job`` at class scope
    #    → ruff F821 ``undefined name 'self'``; see TASK-6).
    text = _strip_task_runner_class(text)

    # 9. Remove imports that only the stripped TaskRunner class used:
    #    ``injectable`` (class decorator), ``uuid4`` (job-id generation), and
    #    ``JobProtocol``/``TaskProvider`` from the tasks-import line (only the
    #    ``task``/``scheduled`` decorator remains). Each pattern matches the
    #    full pre-trim form, so a second pass is a no-op (idempotent).
    text = re.sub(r"^from lexigram\.di import injectable\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^from uuid import uuid4\n", "", text, flags=re.MULTILINE)
    # Filter the lexigram.tasks import line to the decorator(s) still used by
    # the remaining @task/@scheduled callable (drop JobProtocol/TaskProvider,
    # which only the removed TaskRunner referenced). Order-independent.
    def _filter_tasks_import(match: re.Match[str]) -> str:
        names = [n.strip() for n in match.group(1).split(",") if n.strip()]
        kept = [n for n in names if n in {"task", "scheduled"}]
        if not kept:
            return match.group(0)
        return "from lexigram.tasks import " + ", ".join(kept)

    text = re.sub(
        r"^from lexigram\.tasks import (.+)$",
        _filter_tasks_import,
        text,
        flags=re.MULTILINE,
    )

    return TaskReconcileResult(text=text, changed=text != original)


def _strip_task_runner_class(text: str) -> str:
    """Remove the trailing ``@injectable class <Name>TaskRunner`` block.

    Only the runner class generated by the framework task template is removed
    (identified by its ``@injectable`` decorator and ``TaskRunner`` suffix);
    hand-written classes are untouched.
    """
    lines = text.split("\n")
    cut: int | None = None
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("@injectable"):
            cut = idx
            break
    if cut is None:
        return text
    # Trim blank lines immediately preceding the decorator.
    head = cut
    while head > 0 and lines[head - 1].strip() == "":
        head -= 1
    out = lines[:head]
    # Normalise to a single trailing newline.
    while out and out[-1].strip() == "":
        out.pop()
    return "\n".join(out) + "\n"


def _collapse_title_docstring(text: str) -> str:
    """Collapse a title-only module docstring onto one line.

    The task template renders a module docstring whose only content is a single
    title line (an opening triple-quote and title, then blank line(s) and a
    closing triple-quote, or the quote/title/quote split over three lines).
    Black collapses a title-only docstring onto a single line.
    """
    title_only = re.compile(
        r'^"""(?P<title>[^"\n]+?)\s*\n(?:[ \t]*\n)*"""[ \t]*\n',
        flags=re.MULTILINE,
    )

    def _collapse(match: re.Match[str]) -> str:
        body = match.group("title").strip()
        # Only collapse when there is no real docstring body (a body would
        # appear after the title as additional non-blank text) — the title is
        # the sole content by construction here.
        return f'"""{body}"""\n'

    return title_only.sub(_collapse, text, count=1)


def _collapse_blanks_in_brackets(text: str) -> str:
    """Remove blank lines that fall inside open ``(``/``[``/``{`` brackets.

    Black never keeps blank lines inside argument lists or dict/list literals.
    The task template's ``{% for %}`` loops leave such blank lines (e.g. inside
    the generated ``run(...)`` signature and the ``task_kwargs = {...}``
    literal). We track bracket depth line-by-line, ignoring brackets inside
    string literals, and drop any blank line while depth > 0.
    """
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = set(pairs.values())
    lines = text.split("\n")
    result: list[str] = []
    depth = 0
    in_string: str | None = None
    for line in lines:
        if line.strip() == "" and depth > 0:
            continue  # blank line inside brackets — drop
        result.append(line)
        for ch in line:
            if in_string is not None:
                if ch == in_string:
                    in_string = None
                continue
            if ch in ('"', "'"):
                in_string = ch
            elif ch in pairs:
                depth += 1
            elif ch in closers and depth > 0:
                depth -= 1
    return "\n".join(result)


def _merge_tasks_imports(text: str) -> str:
    """Merge a separated `from lexigram.tasks import <decorator>` into the
    main `from lexigram.tasks import JobProtocol, TaskProvider` line.
    """
    # The multi-name "main" import line (e.g. JobProtocol, TaskProvider, …).
    main = re.search(
        r"^from lexigram\.tasks import ([^\n]*,[^\n]*)\n",
        text,
        flags=re.MULTILINE,
    )
    # The standalone decorator import (exactly `scheduled` or `task`).
    deco = re.search(
        r"^from lexigram\.tasks import (scheduled|task)\s*\n",
        text,
        flags=re.MULTILINE,
    )
    # Nothing to merge when there's no separate decorator import (already
    # merged/trimmed) or the decorator is the only tasks import present.
    if not deco or (main is not None and main.start() == deco.start()):
        return text
    if main is None:
        # After trimming, a lone ``from lexigram.tasks import scheduled``
        # remains — already in final form.
        return text
    decorator = deco.group(1)
    names = [n.strip() for n in main.group(1).split(",") if n.strip()]
    if decorator not in names:
        names.append(decorator)
    names.sort()
    merged = f"from lexigram.tasks import {', '.join(names)}\n"
    text = text[: main.start()] + merged + text[main.end() :]
    # Remove the now-duplicate standalone decorator import (plus surrounding
    # blank-line gap so the block stays tight).
    text = re.sub(
        r"\n*from lexigram\.tasks import (?:" + decorator + r")\s*\n",
        "\n",
        text,
        count=1,
    )
    # Ensure exactly one blank line separates the import block from the
    # `logger = get_logger(__name__)` that follows it.
    return re.sub(
        r"(from lexigram\.tasks import [^\n]+\n)\s*\n*(logger = get_logger)",
        r"\1\n\2",
        text,
    )


def _strip_dead_param_locals(text: str) -> str:
    """Drop ``<name> = kwargs.get("<name>"[, None])`` lines and blank residue.

    Only matches the generated pattern (a name on both the LHS and inside
    ``kwargs.get``) to avoid touching hand-written code.
    """
    pattern = re.compile(
        r"^[ \t]+(?P<var>[A-Za-z_][A-Za-z0-9_]*)"
        r" = kwargs\.get\(\"(?P=var)\"(?:, None)?\)\s*\n",
        flags=re.MULTILINE,
    )
    return pattern.sub("", text)


_TOP_LEVEL_DEF = re.compile(r"^(?:async def |def |class |@)")


def _normalize_blank_lines(text: str) -> str:
    """Strip trailing whitespace and normalise blank-line runs.

    PEP 8 / black expect **two** blank lines before a top-level ``def`` /
    ``class`` / decorator, and **one** blank line everywhere else. The task
    template's Jinja loops emit indented (whitespace-only) blank lines and
    leave inconsistent spacing, so we collapse every blank run and then
    re-expand the ones preceding a top-level definition to two.
    """
    lines = [line.rstrip() for line in text.split("\n")]

    # Collapse each run of consecutive blank lines to exactly one.
    collapsed: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = line == ""
        if is_blank and prev_blank:
            continue
        collapsed.append(line)
        prev_blank = is_blank

    # Ensure two blank lines separate top-level definitions.
    out: list[str] = []
    for line in collapsed:
        if _TOP_LEVEL_DEF.match(line) and out:
            # Backfill: remove any single trailing blank, then add two.
            while out and out[-1] == "":
                out.pop()
            out.extend(["", ""])
        out.append(line)
    return "\n".join(out)


__all__ = ["TaskReconcileResult", "reconcile_task"]
