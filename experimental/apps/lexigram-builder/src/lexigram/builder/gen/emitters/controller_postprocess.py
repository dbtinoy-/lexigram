"""Reconcile framework-generated controllers with the flat ``src/app`` layout.

The web package's ``controller`` generator
(``lexigram.web.cli.generators.controller:ControllerGenerator``) renders a
controller that assumes the CLI's project-relative layout. Wherever the layout puts those packages -- flat under ``src/app`` in the
minimal structure, sibling packages at ``src/`` in the structured one --
the template makes two assumptions that do not hold:

1. it imports the repository as ``from repositories.<model>_repository import ...``
   (a bare ``repositories`` package that does not exist on ``sys.path``) —
   see ``docs/LEXIGRAM_FRAMEWORK_BUGS.md`` (LEX-1);
2. it never imports/uses the ``<Name>Create`` / ``<Name>Update`` Pydantic
   models that the SQL ``model`` generator emits (LEX-2), so request bodies
   are unvalidated.

This module applies idempotent, *best-effort* transforms: each step checks
whether its precondition is present and reports what it changed. A generator
that changes its template downstream degrades gracefully (the step is
skipped) rather than corrupting the file or crashing the pipeline.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re

from lexigram.builder.gen.layout import DEFAULT_LAYOUT
from lexigram.logging import get_logger

_logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ControllerRewrite:
    """Outcome of reconciling one generated controller.

    Attributes:
        text: The (possibly rewritten) controller source.
        fixed_imports: True when the repository import was corrected.
        wired_models: True when create/update Pydantic validation was added.
        wired_exception: True when the entity NotFound error was wired.
    """

    text: str
    fixed_imports: bool = False
    wired_models: bool = False
    wired_exception: bool = False

    @property
    def changed(self) -> bool:
        return self.fixed_imports or self.wired_models or self.wired_exception


# `from repositories.note_repository import NoteRepository`
# (or legacy `from .repositories.note_repository import ...`).
_BAD_REPO_IMPORT = re.compile(
    r"^from\s+(?:\.)?repositories\.(?P<module>[a-z0-9_]+)_repository\s+import\s+(?P<cls>[A-Za-z0-9_, ]+)",
    re.MULTILINE,
)

# `from models.note import NoteCreate, NoteUpdate`
# (or legacy `from .models.note import ...`) — sibling package rendered
# against the CLI staging layout; qualify it into the flat app package.
_BAD_MODEL_IMPORT = re.compile(
    r"^from\s+(?:\.)?models\.(?P<module>[a-z0-9_]+)\s+import\s+(?P<cls>[A-Za-z0-9_, ]+)",
    re.MULTILINE,
)

# `raise NotFoundError( ... f"X not found with id: {item_id}" ... )` — spans
# the multi-line form the template emits, non-greedy.
_NOT_FOUND_RAISE = re.compile(
    r"raise NotFoundError\(\s*f?\"[^\"]*not found with id:[^}]*\}\"\s*\)",
    re.DOTALL,
)

# The framework generator now constructs Create/Update DTOs itself; these
# legacy raw-dict call shapes only appear in older templates.
_REPO_CREATE_CALL = re.compile(r"^(\s+)created = await self\.repo\.create\(data\)", re.MULTILINE)
_REPO_UPDATE_CALL = re.compile(r"^(\s+)updated = await self\.repo\.update\(item_id, data\)", re.MULTILINE)


def _imported_names(text: str) -> set[str]:
    """Return every dotted symbol brought in by ``from ... import ...`` lines."""
    names: set[str] = set()
    for match in re.finditer(
        r"^from\s+[\w.]+\s+import\s+(.+)$", text, re.MULTILINE
    ):
        for token in match.group(1).split(","):
            token = token.strip().split(" as ")[0].strip()
            if token:
                names.add(token)
    return names


def reconcile_controller(
    text: str,
    *,
    entity_name: str,
    pascal: str,
    mods: dict[str, str] | None = None,
) -> ControllerRewrite:
    """Reconcile a generated controller's source for *entity_name*.

    Args:
        text: Raw controller source emitted by the framework generator.
        entity_name: snake_case entity name (e.g. ``note``).
        pascal: PascalCase entity/class name (e.g. ``Note``).
        mods: Dotted import paths for this run's structure, from
            :meth:`WriterLayout.module_names`. Repaired imports must name
            the packages the *layout* chose (``app.repositories`` under
            minimal, ``repositories`` under structured), so this is the
            only correct source for them. Defaults to the minimal map.

    Returns:
        A :class:`ControllerRewrite` describing the changes applied.
    """
    mods = mods or DEFAULT_LAYOUT.module_names()
    original = text

    # ── 1. sibling-package imports → absolute app-package paths (LEX-1) ──
    fixed_imports = False

    def _qualify(package: str, suffix: str) -> Callable[[re.Match[str]], str]:
        def _repair(match: re.Match[str]) -> str:
            nonlocal fixed_imports
            fixed_imports = True
            return (
                f"from {mods[package]}.{match.group('module')}{suffix} "
                f"import {match.group('cls').strip()}"
            )

        return _repair

    text = _BAD_REPO_IMPORT.sub(_qualify("repositories", "_repository"), text)
    text = _BAD_MODEL_IMPORT.sub(_qualify("models", ""), text)
    # Drop the stale "resolves against the app source root" comment.
    text = re.sub(
        r"^# resolves against the app source root[^\n]*\n",
        "",
        text,
        flags=re.MULTILINE,
    )

    # ── 2. entity NotFound exception (idempotent) ─────────────────────────
    wired_exception = False
    exc_import = (
        f"from {mods['app']}.exceptions import {pascal}NotFoundError"
    )
    if exc_import not in text:
        # The framework template renders `from lexigram.web.exceptions import
        # <Err, ...>` either as a parenthesised block or a single line —
        # insert our import right after either form.
        block_anchor = "    NotFoundError,\n)"
        single_line = re.search(
            r"^from lexigram\.web\.exceptions import [^\n]+\n", text, re.MULTILINE
        )
        if block_anchor in text:
            text = text.replace(block_anchor, block_anchor + "\n" + exc_import, 1)
            wired_exception = True
        elif single_line:
            text = text.replace(
                single_line.group(0), single_line.group(0) + exc_import + "\n", 1
            )
            wired_exception = True
    else:
        wired_exception = True

    def _replace_not_found(_match: re.Match[str]) -> str:
        nonlocal wired_exception
        wired_exception = True
        return f"raise {pascal}NotFoundError(item_id)"

    text = _NOT_FOUND_RAISE.sub(_replace_not_found, text)

    # ── 3. Pydantic request models for create/update (LEX-2) ──────────────
    # Current framework templates already import/use <Name>Create/Update and
    # ValidationError; we only patch older templates that forwarded raw dicts.
    wired_models = False

    def _create_replacement(match: re.Match[str]) -> str:
        nonlocal wired_models
        wired_models = True
        indent = match.group(1)
        return (
            f"{indent}try:\n"
            f"{indent}    payload = {pascal}Create(**data)\n"
            f"{indent}except ValidationError as exc:\n"
            f"{indent}    raise BadRequestError(str(exc)) from exc\n"
            f"{indent}created = await self.repo.create(payload.model_dump())"
        )

    def _update_replacement(match: re.Match[str]) -> str:
        nonlocal wired_models
        wired_models = True
        indent = match.group(1)
        return (
            f"{indent}try:\n"
            f"{indent}    payload = {pascal}Update(**data)\n"
            f"{indent}except ValidationError as exc:\n"
            f"{indent}    raise BadRequestError(str(exc)) from exc\n"
            f"{indent}updated = await self.repo.update("
            f"item_id, payload.model_dump(exclude_unset=True))"
        )

    new_text, n_create = _REPO_CREATE_CALL.subn(_create_replacement, text)
    new_text, n_update = _REPO_UPDATE_CALL.subn(_update_replacement, new_text)
    if n_create or n_update:
        text = new_text
        # Ensure the supporting symbols are imported in legacy templates.
        model_import = (
            f"from {mods['models']}.{entity_name} import {pascal}Create, "
            f"{pascal}Update"
        )
        if f"{pascal}Create(" in text and f"{pascal}Create" not in _imported_names(text):
            anchor = (
                f"from {mods['repositories']}.{entity_name}_repository"
            )
            if anchor in text:
                text = re.sub(
                    r"^(" + re.escape(anchor) + r"[^\n]*\n)",
                    r"\1" + model_import + "\n",
                    text,
                    count=1,
                    flags=re.MULTILINE,
                )
        if "ValidationError" in text and "from pydantic import ValidationError" not in text:
            text = text.replace(
                "from starlette.requests import Request\n",
                "from starlette.requests import Request\n\nfrom pydantic import ValidationError\n",
                1,
            )

    if text != original:
        _logger.debug(
            "controller_reconciled",
            entity=entity_name,
            fixed_imports=fixed_imports,
            wired_models=wired_models,
            wired_exception=wired_exception,
        )

    return ControllerRewrite(
        text=text,
        fixed_imports=fixed_imports,
        wired_models=wired_models,
        wired_exception=wired_exception,
    )


__all__ = ["ControllerRewrite", "reconcile_controller"]
